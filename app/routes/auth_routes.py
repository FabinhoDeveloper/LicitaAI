from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.config.auth import get_db, create_access_token, set_auth_cookie, clear_auth_cookie
from app.services.auth_service import authenticate_user, has_users
from app.services.user_service import create_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.post("/login")
def login(
    request: Request,
    matricula: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, matricula, senha)
    if not user:
        return RedirectResponse(url="/?erro=credenciais", status_code=302)

    token = create_access_token(data={"sub": user.id})
    redirect_url = "/admin/usuarios" if user.user_type == "admin" else "/home"
    response = RedirectResponse(url=redirect_url, status_code=302)
    set_auth_cookie(response, token)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    clear_auth_cookie(response)
    return response


@router.get("/primeiro-cadastro")
def primeiro_cadastro_form(request: Request, db: Session = Depends(get_db)):
    if has_users(db):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "primeiro_cadastro.html")


@router.post("/primeiro-cadastro")
def primeiro_cadastro(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    matricula: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    confirmar_senha: str = Form(...),
    db: Session = Depends(get_db),
):
    if has_users(db):
        return RedirectResponse(url="/", status_code=302)

    if senha != confirmar_senha:
        return templates.TemplateResponse(
            request,
            "primeiro_cadastro.html",
            {"erro": "As senhas não conferem."},
        )

    try:
        user = create_user(
            db=db,
            first_name=first_name,
            last_name=last_name,
            matricula=matricula,
            email=email,
            password=senha,
            user_type="admin",
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "primeiro_cadastro.html",
            {"erro": str(e)},
        )

    token = create_access_token(data={"sub": user.id})
    response = RedirectResponse(url="/admin/usuarios", status_code=302)
    set_auth_cookie(response, token)
    return response
