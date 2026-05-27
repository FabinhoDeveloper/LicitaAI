from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import User
from app.config.security import hash_password


def get_all_users(db: Session) -> List[User]:
    return db.query(User).order_by(User.id).all()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_matricula(db: Session, matricula: str) -> Optional[User]:
    return db.query(User).filter(User.matricula == matricula).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def count_users(db: Session) -> int:
    return db.query(User).count()


def count_admins(db: Session) -> int:
    return db.query(User).filter(User.user_type == "admin").count()


def create_user(
    db: Session,
    first_name: str,
    last_name: str,
    matricula: str,
    email: str,
    password: str,
    user_type: str = "comum",
) -> User:

    if get_user_by_matricula(db, matricula):
        raise ValueError(f"Matrícula '{matricula}' já está em uso.")
    if get_user_by_email(db, email):
        raise ValueError(f"Email '{email}' já está em uso.")

    user = User(
        first_name=first_name,
        last_name=last_name,
        matricula=matricula,
        email=email,
        password=hash_password(password),
        user_type=user_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    matricula: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    user_type: Optional[str] = None,
) -> User:

    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"Usuário com id {user_id} não encontrado.")

    if matricula and matricula != user.matricula:
        if get_user_by_matricula(db, matricula):
            raise ValueError(f"Matrícula '{matricula}' já está em uso.")
    if email and email != user.email:
        if get_user_by_email(db, email):
            raise ValueError(f"Email '{email}' já está em uso.")

    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if matricula is not None:
        user.matricula = matricula
    if email is not None:
        user.email = email
    if password is not None and password.strip():
        user.password = hash_password(password)
    if user_type is not None:
        user.user_type = user_type

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int, current_user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"Usuário com id {user_id} não encontrado.")

    if user.id == current_user_id:
        raise ValueError("Você não pode excluir seu próprio usuário.")

    if user.user_type == "admin" and count_admins(db) <= 1:
        raise ValueError("Não é possível excluir o último administrador do sistema.")

    db.delete(user)
    db.commit()
