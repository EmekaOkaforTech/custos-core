from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from urllib.parse import quote_plus

from app.models import Base
from sqlalchemy import text

from app.settings import allow_plaintext_db, get_database_key, get_database_url

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return get_database_url()


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    url = get_url()
    if url.startswith("sqlite+pysqlcipher") and not allow_plaintext_db():
        key = get_database_key()
        if not key:
            raise RuntimeError("CUSTOS_DATABASE_KEY is required for migrations.")
        if "password=" not in url:
            encoded = quote_plus(key)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}password={encoded}"
    configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        if not allow_plaintext_db():
            key = get_database_key()
            if not key:
                raise RuntimeError("CUSTOS_DATABASE_KEY is required for migrations.")
            connection.execute(text(f"PRAGMA key = '{key}';"))
            connection.execute(text("PRAGMA cipher_version;"))
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
