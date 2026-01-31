from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.ops.auth import hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])


class UserIn(BaseModel):
    name: str
    email: Optional[str] = None
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: Optional[str] = None


@router.post("", response_model=UserOut)
def create_user(payload: UserIn, db: Session = Depends(get_db)):
    if payload.email:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
    user = User(
        id=f"u_{uuid4().hex}",
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    return UserOut(id=user.id, name=user.name, email=user.email)


class LoginIn(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    password: str


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    if payload.email:
        user = db.query(User).filter(User.email == payload.email).first()
    elif payload.name:
        user = db.query(User).filter(User.name == payload.name).first()
    else:
        raise HTTPException(status_code=400, detail="email or name required")
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"id": user.id, "name": user.name, "email": user.email}
