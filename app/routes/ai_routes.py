from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.auth import get_db, get_current_user
from app.models import User, Document
from app.services.ai_service import (
    generate_document_from_form,
    serialize_secoes,
    deserialize_secoes,
    start_generation,
    get_task_status,
)
from app.services.document_service import create_document, update_document_file_path
from app.services.docx_service import generate_docx, copy_to_exemplos

router = APIRouter(prefix="/documentos")
templates = Jinja2Templates(directory="app/templates")


@router.get("/novo/{tipo}")
def formulario_documento(
    tipo: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    if tipo not in ("dfd", "tr"):
        raise StarletteHTTPException(status_code=404)

    labels = {
        "dfd": "Documento de Formalização da Demanda",
        "tr": "Termo de Referência",
    }

    return templates.TemplateResponse(
        request,
        "gerar_documento.html",
        {
            "request": request,
            "user": user,
            "tipo": tipo,
            "tipo_label": labels.get(tipo, tipo.upper()),
        },
    )


@router.post("/gerar")
def gerar_documento(
    request: Request,
    tipo: str = Form(...),
    titulo: str = Form(...),
    objeto: str = Form(...),
    justificativa: str = Form(...),
    setor_demandante: str = Form(...),
    valor_estimado: str = Form(default=""),
    prazo_execucao: str = Form(default=""),
    modalidade: str = Form(default=""),
    observacoes: str = Form(default=""),
    user: User = Depends(get_current_user),
):
    dados = {
        "objeto": objeto,
        "justificativa": justificativa,
        "setor_demandante": setor_demandante,
        "valor_estimado": valor_estimado or None,
        "prazo_execucao": prazo_execucao or None,
        "modalidade": modalidade or None,
        "observacoes": observacoes or None,
    }

    task_id = start_generation(tipo, titulo, dados)

    return RedirectResponse(
        url=f"/documentos/gerando/{task_id}?tipo={tipo}&titulo={titulo}",
        status_code=302,
    )


@router.get("/gerar-status/{task_id}")
def status_geracao(task_id: str):
    return get_task_status(task_id)


@router.get("/gerando/{task_id}")
def tela_gerando(
    task_id: str,
    request: Request,
    tipo: str = "",
    titulo: str = "",
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request,
        "gerando_documento.html",
        {
            "request": request,
            "user": user,
            "task_id": task_id,
            "tipo": tipo,
            "titulo": titulo,
        },
    )


@router.post("/salvar")
async def salvar_documento(
    request: Request,
    tipo: str = Form(...),
    titulo: str = Form(...),
    fontes_rag: str = Form(default=""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form_data = dict(await request.form())
    secoes_editadas = []
    for key in sorted(form_data.keys()):
        if key.startswith("secao_titulo_"):
            idx = key.replace("secao_titulo_", "")
            secoes_editadas.append({
                "titulo": form_data[key],
                "conteudo": form_data.get(f"secao_conteudo_{idx}", ""),
            })

    if not secoes_editadas:
        raise StarletteHTTPException(status_code=400, detail="Nenhuma seção enviada")

    conteudo_json = serialize_secoes(secoes_editadas)
    fontes_list = [f.strip() for f in fontes_rag.split(",") if f.strip()]

    documento = create_document(
        db=db,
        user_id=user.id,
        title=titulo,
        doc_type=tipo,
        content=conteudo_json,
        fontes_rag=",".join(fontes_list),
    )

    try:
        template_name = f"template_{tipo}.docx"
        docx_path = generate_docx(
            template_name=template_name,
            titulo=titulo,
            secoes=secoes_editadas,
            tipo=tipo,
        )
        update_document_file_path(db, documento.id, docx_path)

        copy_to_exemplos(docx_path)
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return RedirectResponse(url=f"/documentos/{documento.id}", status_code=302)
