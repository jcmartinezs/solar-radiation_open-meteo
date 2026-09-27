from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index, UniqueConstraint, func
from werkzeug.security import check_password_hash, generate_password_hash

from solar_radiation_api.db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=True, unique=True)

    api_key_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
    )

    def set_api_key(self, api_key: str) -> None:
        self.api_key_hash = generate_password_hash(api_key)

    def check_api_key(self, api_key: str) -> bool:
        return check_password_hash(self.api_key_hash, api_key)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Measurement(db.Model):
    __tablename__ = "measurements"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    source = db.Column(db.String(32), nullable=False, default="open-meteo")
    latitude = db.Column(db.Float(asdecimal=False), nullable=False)
    longitude = db.Column(db.Float(asdecimal=False), nullable=False)
    timezone = db.Column(db.String(64), nullable=False, default="UTC")

    interval = db.Column(db.String(16), nullable=False)  # hourly | daily
    variable = db.Column(db.String(64), nullable=False)
    unit = db.Column(db.String(32), nullable=True)

    # Stored as *naive* datetime in the timezone returned by Open-Meteo.
    # Persisting timezone next to it allows unambiguous interpretation.
    timestamp = db.Column(db.DateTime, nullable=False)

    value = db.Column(db.Float(asdecimal=False), nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
    )

    created_by_user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user = db.relationship("User", lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "source",
            "latitude",
            "longitude",
            "timezone",
            "interval",
            "variable",
            "timestamp",
            name="uq_measurement_natural_key",
        ),
        Index(
            "ix_measurements_lookup",
            "latitude",
            "longitude",
            "variable",
            "interval",
            "timestamp",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "interval": self.interval,
            "variable": self.variable,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by_user_id": self.created_by_user_id,
            "created_by_username": self.created_by_user.username if self.created_by_user else None,
        }
