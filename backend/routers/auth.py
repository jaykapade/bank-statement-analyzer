from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
import uuid

from auth import (
    apply_session_cookie,
    clear_session_cookie,
    create_session,
    destroy_session,
    get_current_user,
    get_db,
    hash_password,
    normalize_email,
    serialize_user,
    utcnow,
    verify_password,
)
from config import settings
from models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: str
    password: str


def validate_password(password: str):
    if len(password) < settings.password_min_length:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {settings.password_min_length} characters long",
        )


@router.post("/register", status_code=201)
def register(payload: AuthRequest, response: Response, db=Depends(get_db)):
    email = normalize_email(payload.email)
    validate_password(payload.password)

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(payload.password),
        created_at=utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_session(db, user)
    apply_session_cookie(response, token)

    return {"user": serialize_user(user)}


@router.post("/login")
def login(payload: AuthRequest, response: Response, db=Depends(get_db)):
    email = normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_session(db, user)
    apply_session_cookie(response, token)

    return {"user": serialize_user(user)}


@router.post("/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    destroy_session(db, request.cookies.get(settings.session_cookie_name))
    clear_session_cookie(response)
    return {"message": "Logged out"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"user": serialize_user(current_user)}
