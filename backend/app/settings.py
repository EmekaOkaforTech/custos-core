import os


def get_database_url() -> str:
    database_url = os.getenv("CUSTOS_DATABASE_URL")
    if database_url:
        return database_url
    db_path = os.getenv("CUSTOS_DB_PATH", "custos.db")
    return f"sqlite+pysqlcipher:///{db_path}"


def get_database_key() -> str:
    return os.getenv("CUSTOS_DATABASE_KEY", "")


def allow_plaintext_db() -> bool:
    return os.getenv("CUSTOS_ALLOW_PLAINTEXT_DB", "0") == "1"


def get_data_dir() -> str:
    return os.getenv("CUSTOS_DATA_DIR", "custos-data")


def get_db_path() -> str:
    db_path = os.getenv("CUSTOS_DB_PATH")
    if db_path:
        return db_path
    database_url = get_database_url()
    if database_url.startswith("sqlite"):
        parts = database_url.split(":///")
        if len(parts) == 2:
            return parts[1]
    return "custos.db"


def get_calendar_enabled() -> bool:
    return os.getenv("CUSTOS_CALENDAR_ENABLED", "0") == "1"


def get_calendar_poll_seconds() -> int:
    return int(os.getenv("CUSTOS_CALENDAR_POLL_SECONDS", "900"))
