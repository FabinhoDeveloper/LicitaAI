import json
import re
import threading
import uuid

from app.ai.chains import generate_document


_tasks: dict[str, dict] = {}


_DFD_SECTIONS = [
    "Descrição da necessidade",
    "Justificativa da contratação",
    "Descrição da solução",
    "Estimativa do valor",
    "Alinhamento estratégico",
    "Modalidade de licitação sugerida",
]


def _parse_sections(texto: str, secoes_esperadas: list[str]) -> list[dict]:
    """
    Tenta extrair seções individuais do texto gerado pelo LLM usando regex.
    Se falhar, retorna o texto inteiro como uma única seção.
    """
    pattern = r"\*\*(\d+)\.\s(.+?)\*\*\n?(.*?)(?=\n\*\*\d+\.|\Z)"
    matches = re.findall(pattern, texto, re.DOTALL)

    if len(matches) >= len(secoes_esperadas):
        secoes = []
        for i, titulo_esperado in enumerate(secoes_esperadas):
            secoes.append({
                "titulo": f"{i + 1}. {titulo_esperado}",
                "conteudo": matches[i][2].strip() if i < len(matches) else "",
            })
        return secoes

    secoes = []
    for match in matches:
        num, titulo, conteudo = match
        secoes.append({
            "titulo": f"{num}. {titulo}",
            "conteudo": conteudo.strip(),
        })
    return secoes


def generate_document_from_form(tipo: str, dados: dict) -> dict:
    """
    Orquestra a geração de documento a partir dos dados do formulário.
    """
    resultado = generate_document(tipo, dados)

    if tipo == "dfd":
        secoes = _parse_sections(resultado["texto"], _DFD_SECTIONS)
    else:
        secoes = _parse_sections(resultado["texto"], [])

    if not secoes:
        secoes = [{
            "titulo": "Documento gerado",
            "conteudo": resultado["texto"],
        }]

    return {
        "texto": resultado["texto"],
        "secoes": secoes,
        "fontes_rag": resultado.get("fontes", []),
    }


def serialize_secoes(secoes: list[dict]) -> str:
    """Serializa as seções editadas para armazenamento em formato JSON."""
    return json.dumps(secoes, ensure_ascii=False)


def deserialize_secoes(raw: str) -> list[dict]:
    """Deserializa seções armazenadas em JSON para exibição."""
    return json.loads(raw) if raw else []


def start_generation(tipo: str, titulo: str, dados: dict) -> str:
    """Inicia geração do documento em thread separada. Retorna o task_id."""
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "status": "generating",
        "tipo": tipo,
        "titulo": titulo,
        "secoes": None,
        "fontes_rag": None,
        "error": None,
    }

    def _run():
        try:
            resultado = generate_document_from_form(tipo, dados)
            _tasks[task_id] = {
                "status": "done",
                "tipo": tipo,
                "titulo": titulo,
                "secoes": resultado["secoes"],
                "fontes_rag": resultado["fontes_rag"],
                "error": None,
            }
        except Exception as e:
            _tasks[task_id] = {
                "status": "error",
                "tipo": tipo,
                "titulo": titulo,
                "secoes": None,
                "fontes_rag": None,
                "error": str(e),
            }

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return task_id


def get_task_status(task_id: str) -> dict:
    """Retorna o status atual de uma task de geração."""
    task = _tasks.get(task_id)
    if task is None:
        return {"status": "not_found"}
    return {
        "status": task["status"],
        "tipo": task.get("tipo"),
        "titulo": task.get("titulo"),
        "secoes": task["secoes"],
        "fontes_rag": task["fontes_rag"],
        "error": task["error"],
    }
