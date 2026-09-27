from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenMeteoRequest:
    latitude: float
    longitude: float
    start_date: str
    end_date: str
    timezone: str
    hourly: list[str]
    daily: list[str]
    product: str  # archive | forecast


def fetch_timeseries(req: OpenMeteoRequest, timeout_s: int = 60) -> dict[str, Any]:
    if req.product not in {"archive", "forecast"}:
        raise OpenMeteoError("product must be 'archive' or 'forecast'")

    url = ARCHIVE_URL if req.product == "archive" else FORECAST_URL

    params: dict[str, Any] = {
        "latitude": req.latitude,
        "longitude": req.longitude,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "timezone": req.timezone,
    }

    if req.hourly:
        params["hourly"] = ",".join(req.hourly)
    if req.daily:
        params["daily"] = ",".join(req.daily)

    r = requests.get(url, params=params, timeout=timeout_s)
    if r.status_code >= 400:
        raise OpenMeteoError(f"Open-Meteo error {r.status_code}: {r.text[:300]}")

    payload = r.json()

    # Open-Meteo sometimes includes a structured error message.
    if isinstance(payload, dict) and payload.get("error") is True:
        reason = payload.get("reason") or "Unknown Open-Meteo error"
        raise OpenMeteoError(str(reason))

    return payload
