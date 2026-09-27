import os

from dotenv import load_dotenv
from flask import Flask, Response, request

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

    @app.get("/")
    def index():
        endpoints = {
            "health": "/health",
            "ingest_open_meteo": "/api/ingest/open-meteo",
            "list_measurements": "/api/measurements",
            "who_am_i": "/api/users/me",
            "admin_create_user": "/api/users",
            "admin_list_users": "/api/users",
        }

        wants_html = "text/html" in (request.headers.get("Accept") or "")
        if wants_html:
            body = """<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Solar Radiation API</title>
    <style>
      body { font-family: system-ui, -apple-system, sans-serif; margin: 24px; }
      code { background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }
      li { margin: 8px 0; }
    </style>
  </head>
  <body>
    <h1>Solar Radiation API</h1>
    <p>Endpoints:</p>
    <ul>
      <li><code>GET</code> <a href=\"/health\">/health</a></li>
      <li><code>POST</code> <code>/api/ingest/open-meteo</code> (requires API key)</li>
      <li><code>GET</code> <a href=\"/api/measurements\">/api/measurements</a></li>
      <li><code>GET</code> <code>/api/users/me</code> (requires API key)</li>
      <li><code>POST</code> <code>/api/users</code> (admin only)</li>
      <li><code>GET</code> <code>/api/users</code> (admin only)</li>
    </ul>
    <p>Tip: Use <code>Authorization: Bearer &lt;api_key&gt;</code> for ingestion.</p>
  </body>
</html>"""
            return Response(body, mimetype="text/html")

        return {"service": "solar-radiation-open-meteo", "endpoints": endpoints}

    return app
