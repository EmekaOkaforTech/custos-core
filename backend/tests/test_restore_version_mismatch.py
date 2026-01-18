import os
from pathlib import Path

from app.ops.backup import BACKUP_VERSION
from app.ops.restore import restore_backup


def test_restore_version_mismatch(tmp_path):
    db_path = Path(tmp_path) / "custos.db"
    db_path.write_text("original")

    os.environ["CUSTOS_DB_PATH"] = str(db_path)
    os.environ["CUSTOS_ALLOW_PLAINTEXT_DB"] = "1"

    backup_path = Path(tmp_path) / "backup.db"
    backup_path.write_text("backup")
    meta_path = backup_path.with_suffix(".meta.json")
    meta_path.write_text('{"version": "0"}')

    result = restore_backup(backup_path)
    assert result["status"] == "failed"
    assert result["error"] == "version_mismatch"
    assert db_path.read_text() == "original"
