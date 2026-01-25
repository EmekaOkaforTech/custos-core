from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

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
    url = get_url()
    connect_args = {}
    engine_kwargs = {"poolclass": pool.NullPool}
    if url.startswith("sqlite+pysqlcipher") and not allow_plaintext_db():
        key = get_database_key()
        if not key:
            raise RuntimeError("CUSTOS_DATABASE_KEY is required for migrations.")
        try:
            import sqlcipher3
        except ImportError as exc:
            raise RuntimeError(
                "SQLCipher driver missing. Install sqlcipher3-binary and avoid conda base."
            ) from exc
        url = url.replace("sqlite+pysqlcipher:///", "sqlite:///", 1)
        engine_kwargs["module"] = sqlcipher3.dbapi2
    connectable = create_engine(url, connect_args=connect_args, **engine_kwargs)
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
