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

    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

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


class HourlyMeasurement(db.Model):
    __tablename__ = "hourly_measurements"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    # Spatial aggregation area
    lat_min = db.Column(db.Float(asdecimal=False), nullable=False)
    lat_max = db.Column(db.Float(asdecimal=False), nullable=False)
    lon_min = db.Column(db.Float(asdecimal=False), nullable=False)
    lon_max = db.Column(db.Float(asdecimal=False), nullable=False)

    # Can hold multiple zip codes when the data is identical
    zip_codes = db.Column(db.JSON, nullable=True)

    # Timestamp for the hour (stored as UTC naive datetime)
    timestamp = db.Column(db.DateTime, nullable=False)

    # Variables (one row per hour)
    temperature_2m = db.Column(db.Float(asdecimal=False), nullable=True)
    terrestrial_radiation = db.Column(db.Float(asdecimal=False), nullable=True)
    global_tilted_irradiance = db.Column(db.Float(asdecimal=False), nullable=True)
    direct_normal_irradiance = db.Column(db.Float(asdecimal=False), nullable=True)
    diffuse_radiation = db.Column(db.Float(asdecimal=False), nullable=True)
    direct_radiation = db.Column(db.Float(asdecimal=False), nullable=True)
    shortwave_radiation = db.Column(db.Float(asdecimal=False), nullable=True)
    terrestrial_radiation_instant = db.Column(db.Float(asdecimal=False), nullable=True)
    global_tilted_irradiance_instant = db.Column(db.Float(asdecimal=False), nullable=True)
    direct_normal_irradiance_instant = db.Column(db.Float(asdecimal=False), nullable=True)
    diffuse_radiation_instant = db.Column(db.Float(asdecimal=False), nullable=True)
    direct_radiation_instant = db.Column(db.Float(asdecimal=False), nullable=True)
    shortwave_radiation_instant = db.Column(db.Float(asdecimal=False), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    created_by_user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user = db.relationship("User", lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "lat_min",
            "lat_max",
            "lon_min",
            "lon_max",
            "timestamp",
            name="uq_hourly_measurement_area_time",
        ),
        Index(
            "ix_hourly_measurements_lookup",
            "lat_min",
            "lat_max",
            "lon_min",
            "lon_max",
            "timestamp",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lat_min": self.lat_min,
            "lat_max": self.lat_max,
            "lon_min": self.lon_min,
            "lon_max": self.lon_max,
            "zip_codes": self.zip_codes,
            "timestamp": self.timestamp.isoformat(),
            "temperature_2m": self.temperature_2m,
            "terrestrial_radiation": self.terrestrial_radiation,
            "global_tilted_irradiance": self.global_tilted_irradiance,
            "direct_normal_irradiance": self.direct_normal_irradiance,
            "diffuse_radiation": self.diffuse_radiation,
            "direct_radiation": self.direct_radiation,
            "shortwave_radiation": self.shortwave_radiation,
            "terrestrial_radiation_instant": self.terrestrial_radiation_instant,
            "global_tilted_irradiance_instant": self.global_tilted_irradiance_instant,
            "direct_normal_irradiance_instant": self.direct_normal_irradiance_instant,
            "diffuse_radiation_instant": self.diffuse_radiation_instant,
            "direct_radiation_instant": self.direct_radiation_instant,
            "shortwave_radiation_instant": self.shortwave_radiation_instant,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by_user_id": self.created_by_user_id,
            "created_by_username": self.created_by_user.username if self.created_by_user else None,
        }
