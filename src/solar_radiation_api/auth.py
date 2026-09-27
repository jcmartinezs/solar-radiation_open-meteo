from __future__ import annotations

from functools import wraps

from flask import current_app, g, request

from solar_radiation_api.db import db
from solar_radiation_api.models import User


def _extract_api_key() -> str | None:
    # Prefer standard Bearer token, but also support X-API-Key.
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        return token or None

    token = request.headers.get("X-API-Key", "").strip()
    return token or None


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = _extract_api_key()
        if not api_key:
            return {"error": "Missing API key"}, 401

        # Simple lookup: iterate active users and check hash.
        # For larger user counts, add an api_key_id prefix and index it.
        users = db.session.query(User).filter(User.is_active.is_(True)).all()
        for user in users:
            if user.check_api_key(api_key):
                g.current_user = user
                return fn(*args, **kwargs)

        return {"error": "Invalid API key"}, 401

    return wrapper


def require_admin_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        configured = (current_app.config.get("ADMIN_API_KEY") or "").strip()
        if not configured:
            return {"error": "ADMIN_API_KEY is not configured on the server"}, 500

        provided = request.headers.get("X-Admin-Key", "").strip()
        if provided != configured:
            return {"error": "Invalid admin key"}, 403

        return fn(*args, **kwargs)

    return wrapper
