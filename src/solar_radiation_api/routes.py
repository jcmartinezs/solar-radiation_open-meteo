from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, current_app, g, request
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from solar_radiation_api.auth import require_admin_key, require_api_key
from solar_radiation_api.db import db
from solar_radiation_api.models import HourlyMeasurement, User
from solar_radiation_api.open_meteo import OpenMeteoError, OpenMeteoRequest, fetch_timeseries


api_bp = Blueprint("api", __name__, url_prefix="/api")


DEFAULT_HOURLY_VARIABLES: list[str] = [
    "temperature_2m",
    "terrestrial_radiation",
    "global_tilted_irradiance",
    "direct_normal_irradiance",
    "diffuse_radiation",
    "direct_radiation",
    "shortwave_radiation",
    "terrestrial_radiation_instant",
    "global_tilted_irradiance_instant",
    "direct_normal_irradiance_instant",
    "diffuse_radiation_instant",
    "direct_radiation_instant",
    "shortwave_radiation_instant",
]

ALLOWED_HOURLY_VARIABLES: set[str] = set(DEFAULT_HOURLY_VARIABLES)


_HOURLY_MODEL_COLUMNS: dict[str, str] = {
    "temperature_2m": "temperature_2m",
    "terrestrial_radiation": "terrestrial_radiation",
    "global_tilted_irradiance": "global_tilted_irradiance",
    "direct_normal_irradiance": "direct_normal_irradiance",
    "diffuse_radiation": "diffuse_radiation",
    "direct_radiation": "direct_radiation",
    "shortwave_radiation": "shortwave_radiation",
    "terrestrial_radiation_instant": "terrestrial_radiation_instant",
    "global_tilted_irradiance_instant": "global_tilted_irradiance_instant",
    "direct_normal_irradiance_instant": "direct_normal_irradiance_instant",
    "diffuse_radiation_instant": "diffuse_radiation_instant",
    "direct_radiation_instant": "direct_radiation_instant",
    "shortwave_radiation_instant": "shortwave_radiation_instant",
}


def _parse_iso_datetime(value: str) -> datetime:
    # Handles "YYYY-MM-DDTHH:MM" and "YYYY-MM-DDTHH:MM:SS"
    return datetime.fromisoformat(value)


def _parse_iso_date_to_datetime(value: str) -> datetime:
    d = date.fromisoformat(value)
    return datetime(d.year, d.month, d.day)


def _parse_area(body: dict) -> tuple[float, float, float, float, float, float]:
    if "area" in body and isinstance(body["area"], dict):
        a = body["area"]
        lat_min = float(a["lat_min"])
        lat_max = float(a["lat_max"])
        lon_min = float(a["lon_min"])
        lon_max = float(a["lon_max"])
        lat = (lat_min + lat_max) / 2.0
        lon = (lon_min + lon_max) / 2.0
        return lat_min, lat_max, lon_min, lon_max, lat, lon

    lat = float(body["latitude"])
    lon = float(body["longitude"])
    return lat, lat, lon, lon, lat, lon


def _normalize_zip_codes(body: dict) -> list[str] | None:
    z = body.get("zip_codes")
    if z is None:
        return None
    if isinstance(z, str):
        z = [s.strip() for s in z.split(",") if s.strip()]
    if not isinstance(z, list):
        raise ValueError("zip_codes must be a list or comma-separated string")
    out = []
    for item in z:
        s = str(item).strip()
        if s:
            out.append(s)
    return sorted(set(out))


def _payload_to_hourly_rows(
    payload: dict,
    *,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    zip_codes: list[str] | None,
    requested_hourly: list[str],
    created_by_user_id: int | None,
) -> tuple[list[HourlyMeasurement], dict]:
    block = payload.get("hourly") or {}
    times: list[str] = block.get("time") or []

    created: list[HourlyMeasurement] = []

    series: dict[str, list] = {}
    for variable in requested_hourly:
        values = block.get(variable)
        if not isinstance(values, list):
            continue
        series[variable] = values

    for idx, t in enumerate(times):
        ts = _parse_iso_datetime(t)
        row = HourlyMeasurement(
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
            zip_codes=zip_codes,
            timestamp=ts,
            created_by_user_id=created_by_user_id,
        )

        for variable, values in series.items():
            if idx >= len(values):
                continue
            v = values[idx]
            column_name = _HOURLY_MODEL_COLUMNS.get(variable)
            if not column_name:
                continue
            setattr(row, column_name, float(v) if v is not None else None)

        created.append(row)

    meta = {
        "interval": "hourly",
        "n": len(created),
    }
    return created, meta


@api_bp.post("/ingest/open-meteo")
@require_api_key
def ingest_open_meteo():
    body = request.get_json(silent=True) or {}

    try:
        start_date = str(body["start_date"])
        end_date = str(body["end_date"])
        lat_min, lat_max, lon_min, lon_max, latitude, longitude = _parse_area(body)
        zip_codes = _normalize_zip_codes(body)
    except (KeyError, ValueError, TypeError) as e:
        return {
            "error": "Invalid request. Provide start_date/end_date and either latitude/longitude or area.",
            "details": str(e),
        }, 400

    hourly = body.get("hourly")
    if hourly is None or hourly == []:
        hourly = DEFAULT_HOURLY_VARIABLES
    daily = body.get("daily") or []
    if daily:
        return {"error": "daily ingestion is not supported by this schema (hourly only)"}, 400
    if not isinstance(hourly, list):
        return {"error": "hourly must be a list"}, 400

    invalid_hourly = sorted({str(v) for v in hourly if str(v) not in ALLOWED_HOURLY_VARIABLES})
    if invalid_hourly:
        return {
            "error": "Unsupported hourly variables",
            "invalid_hourly": invalid_hourly,
            "allowed_hourly": sorted(ALLOWED_HOURLY_VARIABLES),
        }, 400

    product = str(body.get("product") or current_app.config.get("OPEN_METEO_PRODUCT", "archive"))
    # We store timestamps without timezone. Force UTC to keep them consistent.
    timezone = "UTC"
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
    meta: dict = {"hourly": None}

    current_user_id = getattr(getattr(g, "current_user", None), "id", None)

    rows, interval_meta = _payload_to_hourly_rows(
        payload,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        zip_codes=zip_codes,
        requested_hourly=[str(x) for x in hourly],
        created_by_user_id=current_user_id,
    )
    meta["hourly"] = interval_meta

    if not rows:
        return {"inserted": 0, "meta": meta, "warning": "No hourly rows found"}

    if replace_existing:
        min_ts = min(r.timestamp for r in rows)
        max_ts = max(r.timestamp for r in rows)
        db.session.query(HourlyMeasurement).filter(
            and_(
                HourlyMeasurement.lat_min == lat_min,
                HourlyMeasurement.lat_max == lat_max,
                HourlyMeasurement.lon_min == lon_min,
                HourlyMeasurement.lon_max == lon_max,
                HourlyMeasurement.timestamp >= min_ts,
                HourlyMeasurement.timestamp <= max_ts,
            )
        ).delete(synchronize_session=False)

    try:
        db.session.bulk_save_objects(rows)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {
            "error": "Insert failed due to duplicates. Try replace_existing=true.",
        }, 409

    inserted += len(rows)

    return {
        "inserted": inserted,
        "request": {
            "latitude": latitude,
            "longitude": longitude,
            "area": {
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max,
            },
            "zip_codes": zip_codes,
            "start_date": start_date,
            "end_date": end_date,
            "timezone": timezone,
            "product": product,
            "hourly": hourly,
            "replace_existing": replace_existing,
        },
        "meta": meta,
    }


@api_bp.get("/users/me")
@require_api_key
def get_me():
    user = getattr(g, "current_user", None)
    return {"user": user.to_dict() if user else None}


@api_bp.post("/users")
@require_admin_key
def create_user():
    body = request.get_json(silent=True) or {}

    username = body.get("username")
    api_key = body.get("api_key")
    email = body.get("email")

    if not username or not api_key:
        return {"error": "username and api_key are required"}, 400

    user = User(username=str(username).strip(), email=str(email).strip() if email else None)
    user.set_api_key(str(api_key))

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": "username or email already exists"}, 409

    return {"user": user.to_dict()}, 201


@api_bp.get("/users")
@require_admin_key
def list_users():
    users = db.session.query(User).order_by(User.id.asc()).all()
    return {"count": len(users), "items": [u.to_dict() for u in users]}


@api_bp.get("/measurements")
def list_measurements():
    # Filters
    lat_min = request.args.get("lat_min", type=float)
    lat_max = request.args.get("lat_max", type=float)
    lon_min = request.args.get("lon_min", type=float)
    lon_max = request.args.get("lon_max", type=float)
    start = request.args.get("start")
    end = request.args.get("end")

    limit = request.args.get("limit", default=500, type=int)
    limit = max(1, min(limit, 5000))

    q = db.session.query(HourlyMeasurement)

    if lat_min is not None:
        q = q.filter(HourlyMeasurement.lat_min == lat_min)
    if lat_max is not None:
        q = q.filter(HourlyMeasurement.lat_max == lat_max)
    if lon_min is not None:
        q = q.filter(HourlyMeasurement.lon_min == lon_min)
    if lon_max is not None:
        q = q.filter(HourlyMeasurement.lon_max == lon_max)

    if start:
        q = q.filter(
            HourlyMeasurement.timestamp
            >= (_parse_iso_datetime(start) if "T" in start else _parse_iso_date_to_datetime(start))
        )
    if end:
        q = q.filter(
            HourlyMeasurement.timestamp
            <= (_parse_iso_datetime(end) if "T" in end else _parse_iso_date_to_datetime(end))
        )

    q = q.order_by(HourlyMeasurement.timestamp.asc()).limit(limit)
    items = [m.to_dict() for m in q.all()]
    return {"count": len(items), "items": items}
