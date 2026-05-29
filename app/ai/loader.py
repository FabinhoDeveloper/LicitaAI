import hashlib
import json
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.ai.config import get_ai_config
from app.ai.vector_store import get_vector_store


def _compute_file_hash(file_path: Path) -> str:
    """SHA256 dos primeiros 64 KB + tamanho do arquivo (rápido e suficiente)."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        sha.update(f.read(65536))
    sha.update(str(file_path.stat().st_size).encode())
    return sha.hexdigest()


def _load_state() -> dict:
    """Carrega o estado de ingestão do arquivo JSON."""
    config = get_ai_config()
    state_path = Path(config.ingestion_state_path)
    if not state_path.exists():
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict) -> None:
    """Persiste o estado de ingestão no arquivo JSON."""
    config = get_ai_config()
    state_path = Path(config.ingestion_state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _load_file(file_path: str) -> list[Document]:
    """Carrega um arquivo de acordo com sua extensão."""
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in (".docx", ".doc"):
        loader = Docx2txtLoader(file_path)
    elif ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Formato de arquivo não suportado: {ext}")

    return loader.load()


def _get_splitter() -> RecursiveCharacterTextSplitter:
    config = get_ai_config()
    return RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True,
    )


def ingest_directory(
    directory: str,
    source_type: str = "referencia",
    force: bool = False,
) -> int:
    """
    Carrega documentos de um diretório, divide em chunks,
    gera embeddings e insere no ChromaDB.

    Por padrão, usa estado incremental: apenas arquivos novos ou
    modificados são processados. Use force=True para re-ingestar tudo.

    Args:
        directory: Caminho do diretório com os arquivos.
        source_type: 'referencia' (leis, decretos) ou 'exemplo' (modelos antigos).
        force: Se True, ignora o estado e processa todos os arquivos.

    Returns:
        Número de chunks inseridos.
    """
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {directory}")

    state = _load_state()
    source_state = state.get(source_type, {})
    supported_exts = {".pdf", ".docx", ".doc", ".txt"}

    files_in_dir: dict[str, Path] = {}
    for file_path in path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_exts:
            files_in_dir[file_path.name] = file_path

    files_to_ingest: list[Path] = []
    skipped = 0
    new_state: dict[str, str] = {}

    for filename, file_path in sorted(files_in_dir.items()):
        file_hash = _compute_file_hash(file_path)

        if not force and filename in source_state and source_state[filename] == file_hash:
            skipped += 1
        else:
            files_to_ingest.append(file_path)

        new_state[filename] = file_hash

    if not files_to_ingest:
        print(
            f"[loader] {source_type}: {len(files_in_dir)} arquivo(s) verificados, "
            f"nenhum novo/modificado, {skipped} ignorado(s)"
        )
        return 0

    print(
        f"[loader] {source_type}: {len(files_in_dir)} arquivo(s) no diretório, "
        f"{len(files_to_ingest)} novo(s)/modificado(s), {skipped} ignorado(s)"
    )

    all_docs: list[Document] = []
    for file_path in files_to_ingest:
        try:
            docs = _load_file(str(file_path))
            for doc in docs:
                doc.metadata["source_file"] = file_path.name
                doc.metadata["source_type"] = source_type
            all_docs.extend(docs)
        except Exception as e:
            print(f"[loader] Erro ao carregar {file_path.name}: {e}")

    if not all_docs:
        print(f"[loader] Nenhum documento carregado em {directory}")
        return 0

    splitter = _get_splitter()
    chunks = splitter.split_documents(all_docs)

    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    state[source_type] = new_state
    _save_state(state)

    config = get_ai_config()
    print(
        f"[loader] {len(all_docs)} docs → {len(chunks)} chunks "
        f"inseridos no ChromaDB (coleção: {config.chroma_collection_name})"
    )
    return len(chunks)


def ingest_all(force: bool = False) -> dict[str, int]:
    """
    Varre os diretórios de referências e exemplos e popula o ChromaDB.

    Por padrão, apenas arquivos novos/modificados são processados.
    Use force=True para re-processar tudo do zero.

    Uso:
        python -c "from app.ai.loader import ingest_all; ingest_all()"
        python -c "from app.ai.loader import ingest_all; ingest_all(force=True)"
    """
    config = get_ai_config()
    resultados = {}

    for dir_path, label in [
        (config.referencias_dir, "referencias"),
        (config.exemplos_dir, "exemplos"),
    ]:
        count = ingest_directory(dir_path, source_type=label, force=force)
        resultados[label] = count

    return resultados
