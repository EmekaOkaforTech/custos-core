from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.nas_backup_target import NasBackupTarget
from app.ops.backup import run_nas_backup, verify_nas_backup

router = APIRouter(prefix="/api/backup", tags=["backup"])


class BackupTargetPayload(BaseModel):
    protocol: str = Field(..., pattern="^(smb|nfs)$")
    host: Optional[str] = None
    share: Optional[str] = None
    mount_path: str
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = False


class BackupAction(BaseModel):
    action: str


@router.get("/target")
def get_target(db: Session = Depends(get_db)) -> dict:
    target = db.query(NasBackupTarget).first()
    if not target:
        return {
            "protocol": "smb",
            "host": "",
            "share": "",
            "mount_path": "",
            "username": "",
            "enabled": False,
        }
    return {
        "id": target.id,
        "protocol": target.protocol,
        "host": target.host,
        "share": target.share,
        "mount_path": target.mount_path,
        "username": target.username,
        "enabled": target.enabled,
    }


@router.put("/target")
def upsert_target(payload: BackupTargetPayload, db: Session = Depends(get_db)) -> dict:
    target = db.query(NasBackupTarget).first()
    if target is None:
        target = NasBackupTarget(id=f"nas_{uuid4().hex}")
        db.add(target)
    target.protocol = payload.protocol
    target.host = payload.host
    target.share = payload.share
    target.mount_path = payload.mount_path
    target.username = payload.username
    target.password = payload.password
    target.enabled = payload.enabled
    target.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "saved"}


@router.post("/nas/run")
def run_nas(db: Session = Depends(get_db)) -> dict:
    target = db.query(NasBackupTarget).first()
    if not target or not target.enabled:
        raise HTTPException(status_code=400, detail="nas_backup_not_configured")
    result = run_nas_backup(target.mount_path)
    target.last_backup_at = datetime.utcnow()
    target.last_error = result.get("nas", {}).get("error")
    db.commit()
    return result


@router.post("/nas/verify")
def verify_nas(db: Session = Depends(get_db)) -> dict:
    target = db.query(NasBackupTarget).first()
    if not target or not target.enabled:
        raise HTTPException(status_code=400, detail="nas_backup_not_configured")
    result = verify_nas_backup(target.mount_path)
    target.last_error = result.get("error")
    db.commit()
    return result
