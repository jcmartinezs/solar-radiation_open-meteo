from __future__ import annotations

import click
from flask import Flask

from solar_radiation_api.db import db


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        """Create database tables (no migrations required)."""
        db.create_all()
        click.echo("Database tables created")
