from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.config.auth import get_db, require_admin
from app.models import User
from app.services.user_service import (
    get_all_users,
    get_user_by_id,
    create_user,
    update_user,
    delete_user,
)

router = APIRouter(prefix="/admin/usuarios")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    users = get_all_users(db)
    return templates.TemplateResponse(
        request,
        "admin/usuarios.html",
        {"request": request, "admin": admin, "user": admin, "users": users},
    )


@router.post("")
def create(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    matricula: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    user_type: str = Form("comum"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        create_user(
            db=db,
            first_name=first_name,
            last_name=last_name,
            matricula=matricula,
            email=email,
            password=senha,
            user_type=user_type,
        )
    except ValueError as e:
        users = get_all_users(db)
        return templates.TemplateResponse(
            request,
            "admin/usuarios.html",
            {"request": request, "admin": admin, "user": admin, "users": users, "erro": str(e)},
        )
    return RedirectResponse(url="/admin/usuarios", status_code=302)


@router.post("/{user_id}/editar")
def edit(
    request: Request,
    user_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    matricula: str = Form(...),
    email: str = Form(...),
    senha: str = Form(""),
    user_type: str = Form("comum"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        update_user(
            db=db,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            matricula=matricula,
            email=email,
            password=senha if senha.strip() else None,
            user_type=user_type,
        )
    except ValueError as e:
        users = get_all_users(db)
        return templates.TemplateResponse(
            request,
            "admin/usuarios.html",
            {
                "request": request,
                "admin": admin, "user": admin,
                "users": users,
                "erro": str(e),
                "edit_user_id": user_id,
            },
        )
    return RedirectResponse(url="/admin/usuarios", status_code=302)


@router.post("/{user_id}/excluir")
def delete(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        delete_user(db=db, user_id=user_id, current_user_id=admin.id)
    except ValueError as e:
        users = get_all_users(db)
        return templates.TemplateResponse(
            request,
            "admin/usuarios.html",
            {"request": request, "admin": admin, "user": admin, "users": users, "erro": str(e)},
        )
    return RedirectResponse(url="/admin/usuarios", status_code=302)
