from datetime import datetime
import shutil
from pathlib import Path

from docxtpl import DocxTemplate

TEMPLATES_DIR = Path("app/data/templates")
OUTPUT_DIR = Path("app/data/documentos_gerados")
EXEMPLOS_DIR = Path("app/data/exemplos")


def ensure_directories() -> None:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EXEMPLOS_DIR.mkdir(parents=True, exist_ok=True)


def generate_docx(
    template_name: str,
    titulo: str,
    secoes: list[dict],
    tipo: str = "dfd",
) -> str:
    """
    Gera um arquivo .docx a partir de um template base com timbrado.

    O template deve conter placeholders Jinja2:
        {{ titulo }}
        {% for secao in secoes %}
            {{ secao.titulo }}
            {{ secao.conteudo }}
        {% endfor %}

    Args:
        template_name: Nome do arquivo .docx template (ex: 'template_dfd.docx')
        titulo: Título do documento
        secoes: Lista de seções [{"titulo": ..., "conteudo": ...}]
        tipo: Tipo do documento ('dfd' ou 'tr')

    Returns:
        Caminho absoluto do arquivo .docx gerado
    """
    ensure_directories()

    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template não encontrado: {template_path}\n"
            f"Crie o arquivo {template_path} no Word com o timbrado da prefeitura "
            f"e os placeholders Jinja2 ({{{{ titulo }}}}, "
            f"{{% for secao in secoes %}}...{{% endfor %}})."
        )

    doc = DocxTemplate(str(template_path))

    context = {
        "titulo": titulo,
        "tipo": tipo.upper(),
        "secoes": secoes,
        "data_geracao": datetime.now().strftime("%d/%m/%Y às %H:%M"),
    }

    doc.render(context)

    safe_titulo = "".join(c for c in titulo if c.isalnum() or c in (" ", "-", "_")).strip()
    safe_titulo = safe_titulo[:80].replace(" ", "_")
    filename = f"{tipo}_{safe_titulo}.docx"
    output_path = OUTPUT_DIR / filename

    doc.save(str(output_path))

    return str(output_path.absolute())


def copy_to_exemplos(docx_path: str) -> str:
    """
    Copia o DOCX gerado para o diretório de exemplos,
    para que futuramente seja usado no treinamento via RAG.
    """
    ensure_directories()

    src = Path(docx_path)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {docx_path}")

    dest = EXEMPLOS_DIR / src.name

    suffix = 1
    while dest.exists():
        stem = src.stem
        dest = EXEMPLOS_DIR / f"{stem}_{suffix}{src.suffix}"
        suffix += 1

    shutil.copy2(str(src), str(dest))

    return str(dest.absolute())
