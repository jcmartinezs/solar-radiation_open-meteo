import os


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _build_database_url_from_env() -> str:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    db = os.getenv("MYSQL_DB", "solar_radiation")
    user = os.getenv("MYSQL_USER", "solar_api")
    password = os.getenv("MYSQL_PASSWORD", "")

    # NOTE: password may contain special chars; for robust handling
    # in production prefer setting DATABASE_URL explicitly.
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


def load_config() -> dict:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = _build_database_url_from_env()

    # Keep defaults safe for MySQL
    engine_options: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    return {
        "SQLALCHEMY_DATABASE_URI": database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": engine_options,
        "JSON_SORT_KEYS": False,
        "OPEN_METEO_PRODUCT": os.getenv("OPEN_METEO_PRODUCT", "archive").strip(),
        "OPEN_METEO_TIMEZONE": os.getenv("OPEN_METEO_TIMEZONE", "UTC").strip(),
        "PROPAGATE_EXCEPTIONS": True,
        "DEBUG": _truthy(os.getenv("FLASK_DEBUG")),
    }
