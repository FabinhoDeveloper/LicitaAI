from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config.auth import get_db, get_current_user, require_admin
from app.models import User
from app.services.auth_service import has_users
from app.services.document_service import get_user_documents

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
def home(
    request: Request,
    search: str = Query(default=""),
    order_by: str = Query(default="created_at_desc"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    documentos = get_user_documents(db, user.id, search=search or None, order_by=order_by)
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "user": user,
            "documentos": documentos,
            "search": search,
            "order_by": order_by,
        },
    )


@router.get("/admin")
def admin(request: Request, admin: User = Depends(require_admin)):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"request": request, "admin": admin},
    )
