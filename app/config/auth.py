import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models import User

SECRET_KEY = os.getenv(
    "SECRET_KEY",
)
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["sub"] = str(to_encode.get("sub", ""))
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request) -> User:
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.user_type != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return current_user


def set_auth_cookie(response: RedirectResponse, token: str):
    response.set_cookie(
        key="licitai_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def clear_auth_cookie(response: RedirectResponse):
    response.delete_cookie(key="licitai_token")
