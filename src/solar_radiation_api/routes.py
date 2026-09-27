from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, current_app, request
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from solar_radiation_api.db import db
from solar_radiation_api.models import Measurement
from solar_radiation_api.open_meteo import OpenMeteoError, OpenMeteoRequest, fetch_timeseries


api_bp = Blueprint("api", __name__, url_prefix="/api")


def _parse_iso_datetime(value: str) -> datetime:
    # Handles "YYYY-MM-DDTHH:MM" and "YYYY-MM-DDTHH:MM:SS"
    return datetime.fromisoformat(value)


def _parse_iso_date_to_datetime(value: str) -> datetime:
    d = date.fromisoformat(value)
    return datetime(d.year, d.month, d.day)


def _payload_to_measurements(payload: dict, interval: str) -> tuple[list[Measurement], dict]:
    block = payload.get(interval) or {}
    time_key = block.get("time") or []

    units = payload.get(f"{interval}_units") or {}
    timezone = payload.get("timezone") or current_app.config.get("OPEN_METEO_TIMEZONE", "UTC")

    created: list[Measurement] = []

    for variable, values in block.items():
        if variable == "time":
            continue
        if not isinstance(values, list):
            continue

        unit = units.get(variable)

        # Open-Meteo gives hourly times as ISO datetimes and daily times as ISO dates.
        for t, v in zip(time_key, values, strict=False):
            ts = _parse_iso_datetime(t) if interval == "hourly" else _parse_iso_date_to_datetime(t)
            created.append(
                Measurement(
                    source="open-meteo",
                    latitude=float(payload["latitude"]),
                    longitude=float(payload["longitude"]),
                    timezone=str(timezone),
                    interval=interval,
                    variable=str(variable),
                    unit=str(unit) if unit is not None else None,
                    timestamp=ts,
                    value=float(v) if v is not None else None,
                )
            )

    meta = {
        "interval": interval,
        "timezone": timezone,
        "n": len(created),
    }
    return created, meta


@api_bp.post("/ingest/open-meteo")
def ingest_open_meteo():
    body = request.get_json(silent=True) or {}

    try:
        latitude = float(body["latitude"])
        longitude = float(body["longitude"])
        start_date = str(body["start_date"])
        end_date = str(body["end_date"])
    except (KeyError, ValueError, TypeError):
        return {"error": "latitude, longitude, start_date, end_date are required"}, 400

    hourly = body.get("hourly") or []
    daily = body.get("daily") or []
    if not isinstance(hourly, list) or not isinstance(daily, list):
        return {"error": "hourly and daily must be lists"}, 400

    product = str(body.get("product") or current_app.config.get("OPEN_METEO_PRODUCT", "archive"))
    timezone = str(body.get("timezone") or current_app.config.get("OPEN_METEO_TIMEZONE", "UTC"))
    replace_existing = bool(body.get("replace_existing", True))

    req_obj = OpenMeteoRequest(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        timezone=timezone,
        hourly=[str(x) for x in hourly],
        daily=[str(x) for x in daily],
        product=product,
    )

    try:
        payload = fetch_timeseries(req_obj)
    except OpenMeteoError as e:
        return {"error": str(e)}, 502

    inserted = 0
    meta: dict = {"hourly": None, "daily": None}

    for interval in ("hourly", "daily"):
        if interval == "hourly" and not hourly:
            continue
        if interval == "daily" and not daily:
            continue

        rows, interval_meta = _payload_to_measurements(payload, interval)
        meta[interval] = interval_meta

        if not rows:
            continue

        if replace_existing:
            min_ts = min(r.timestamp for r in rows)
            max_ts = max(r.timestamp for r in rows)
            variables = sorted({r.variable for r in rows})
            tz = interval_meta.get("timezone")

            db.session.query(Measurement).filter(
                and_(
                    Measurement.source == "open-meteo",
                    Measurement.latitude == latitude,
                    Measurement.longitude == longitude,
                    Measurement.timezone == str(tz),
                    Measurement.interval == interval,
                    Measurement.variable.in_(variables),
                    Measurement.timestamp >= min_ts,
                    Measurement.timestamp <= max_ts,
                )
            ).delete(synchronize_session=False)

        try:
            db.session.bulk_save_objects(rows)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {
                "error": "Insert failed due to duplicates. Try replace_existing=true.",
                "details": {
                    "interval": interval,
                },
            }, 409

        inserted += len(rows)

    return {
        "inserted": inserted,
        "request": {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "timezone": timezone,
            "product": product,
            "hourly": hourly,
            "daily": daily,
            "replace_existing": replace_existing,
        },
        "meta": meta,
    }


@api_bp.get("/measurements")
def list_measurements():
    # Filters
    latitude = request.args.get("latitude", type=float)
    longitude = request.args.get("longitude", type=float)
    variable = request.args.get("variable")
    interval = request.args.get("interval")
    start = request.args.get("start")
    end = request.args.get("end")

    limit = request.args.get("limit", default=500, type=int)
    limit = max(1, min(limit, 5000))

    q = db.session.query(Measurement)

    if latitude is not None:
        q = q.filter(Measurement.latitude == latitude)
    if longitude is not None:
        q = q.filter(Measurement.longitude == longitude)
    if variable:
        q = q.filter(Measurement.variable == variable)
    if interval:
        q = q.filter(Measurement.interval == interval)

    if start:
        q = q.filter(Measurement.timestamp >= _parse_iso_datetime(start) if "T" in start else _parse_iso_date_to_datetime(start))
    if end:
        q = q.filter(Measurement.timestamp <= _parse_iso_datetime(end) if "T" in end else _parse_iso_date_to_datetime(end))

    q = q.order_by(Measurement.timestamp.asc()).limit(limit)
    items = [m.to_dict() for m in q.all()]
    return {"count": len(items), "items": items}
