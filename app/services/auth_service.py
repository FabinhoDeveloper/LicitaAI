from typing import Optional

from sqlalchemy.orm import Session

from app.models import User
from app.config.security import verify_password
from app.services.user_service import get_user_by_matricula, count_users


def authenticate_user(db: Session, matricula: str, password: str) -> Optional[User]:
    user = get_user_by_matricula(db, matricula)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def has_users(db: Session) -> bool:
    return count_users(db) > 0
