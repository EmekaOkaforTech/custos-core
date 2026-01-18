import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def test_migrations_run(tmp_path):
    db_path = Path(tmp_path) / "migrate.db"
    os.environ["CUSTOS_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["CUSTOS_ALLOW_PLAINTEXT_DB"] = "1"
    os.environ["CUSTOS_DATABASE_KEY"] = "test-key"
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(config_path))
    command.upgrade(config, "head")
    assert db_path.exists()
