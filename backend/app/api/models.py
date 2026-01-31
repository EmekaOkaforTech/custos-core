from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.model_artifact import ModelArtifact

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelRegisterRequest(BaseModel):
    name: str
    version: str
    path: str
    format: str | None = None
    accelerator: str | None = None


class ModelResponse(BaseModel):
    id: str
    name: str
    version: str
    path: str
    format: str | None
    accelerator: str | None
    checksum: str | None
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[ModelResponse])
def list_models(db: Session = Depends(get_db)) -> list[ModelResponse]:
    models = db.query(ModelArtifact).order_by(ModelArtifact.created_at.desc()).all()
    return [
        ModelResponse(
            id=model.id,
            name=model.name,
            version=model.version,
            path=model.path,
            format=model.format,
            accelerator=model.accelerator,
            checksum=model.checksum,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        for model in models
    ]


@router.post("/register", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
def register_model(request: ModelRegisterRequest, db: Session = Depends(get_db)) -> ModelResponse:
    if not request.name.strip():
        raise HTTPException(status_code=422, detail="name must not be blank")
    if not request.version.strip():
        raise HTTPException(status_code=422, detail="version must not be blank")
    if not request.path.strip():
        raise HTTPException(status_code=422, detail="path must not be blank")

    model_path = Path(request.path)
    if not model_path.exists():
        raise HTTPException(status_code=422, detail="path does not exist")

    checksum = None
    try:
        hasher = sha256()
        with model_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                hasher.update(chunk)
        checksum = hasher.hexdigest()
    except Exception:
        checksum = None

    model = ModelArtifact(
        id="m_" + uuid4().hex,
        name=request.name.strip(),
        version=request.version.strip(),
        path=str(model_path),
        format=request.format,
        accelerator=request.accelerator,
        checksum=checksum,
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return ModelResponse(
        id=model.id,
        name=model.name,
        version=model.version,
        path=model.path,
        format=model.format,
        accelerator=model.accelerator,
        checksum=model.checksum,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
