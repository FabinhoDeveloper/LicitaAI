from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config.auth import get_db, get_current_user, require_admin
from app.models import User
from app.services.auth_service import has_users

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    sem_usuarios = not has_users(db)
    erro = request.query_params.get("erro")
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "sem_usuarios": sem_usuarios, "erro": erro},
    )


@router.get("/home")
def comum(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        request,
        "comum.html",
        {"request": request, "user": user},
    )


@router.get("/admin")
def admin(request: Request, admin: User = Depends(require_admin)):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"request": request, "admin": admin},
    )
