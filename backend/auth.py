from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
import uuid

from fastapi import Depends, HTTPException, Request, Response, status

from config import settings
from db import SessionLocal
from models import Session, User


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def utcnow():
    return datetime.utcnow()


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    return normalized


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        settings.password_hash_iterations,
    )
    return f"pbkdf2_sha256${settings.password_hash_iterations}${salt}${derived_key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iteration_count, salt, expected_hash = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iteration_count),
    )
    return hmac.compare_digest(derived_key.hex(), expected_hash)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def clear_existing_sessions(db, user_id: str):
    db.query(Session).filter(Session.user_id == user_id).delete(
        synchronize_session=False
    )


def create_session(db, user: User) -> str:
    token = secrets.token_urlsafe(32)
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=hash_session_token(token),
        created_at=utcnow(),
        expires_at=utcnow() + timedelta(seconds=settings.session_max_age_seconds),
    )
    clear_existing_sessions(db, user.id)
    db.add(session)
    db.commit()
    return token


def apply_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        path="/",
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(
        key=settings.session_cookie_name, path="/", samesite="lax"
    )


def destroy_session(db, token: str | None):
    if not token:
        return

    db.query(Session).filter(
        Session.token_hash == hash_session_token(token)
    ).delete(synchronize_session=False)
    db.commit()


def serialize_user(user: User):
    return {
        "id": user.id,
        "email": user.email,
    }


def get_current_user(request: Request, db=Depends(get_db)) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    session = (
        db.query(Session)
        .filter(
            Session.token_hash == hash_session_token(token),
            Session.expires_at > utcnow(),
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return user
