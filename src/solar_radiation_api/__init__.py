import os

from dotenv import load_dotenv
from flask import Flask

from solar_radiation_api.cli import register_cli
from solar_radiation_api.config import load_config
from solar_radiation_api.db import db, migrate
from solar_radiation_api.routes import api_bp


def create_app() -> Flask:
    # Load .env if present (safe: ignored in prod)
    load_dotenv(override=False)

    app = Flask(__name__)
    app.config.from_mapping(load_config())

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(api_bp)
    register_cli(app)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "solar-radiation-open-meteo",
            "env": os.getenv("FLASK_ENV", "development"),
        }

    return app
