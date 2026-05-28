from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.auth import get_db, get_current_user
from app.models import User
from app.services.document_service import get_document_by_id

router = APIRouter(prefix="/documentos")
templates = Jinja2Templates(directory="app/templates")


@router.get("/novo")
def novo_documento(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        request,
        "novo_documento.html",
        {"request": request, "user": user},
    )


@router.get("/{document_id}")
def visualizar_documento(
    document_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    documento = get_document_by_id(db, document_id)
    if not documento or documento.user_id != user.id:
        raise StarletteHTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "visualizar_documento.html",
        {"request": request, "user": user, "documento": documento},
    )


@router.get("/{document_id}/download")
def download_documento(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    documento = get_document_by_id(db, document_id)
    if not documento or documento.user_id != user.id:
        raise StarletteHTTPException(status_code=404)
    if not documento.file_path:
        raise StarletteHTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(documento.file_path, filename=f"{documento.title}.docx")
