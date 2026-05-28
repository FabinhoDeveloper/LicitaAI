import os
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


def ingest_directory(directory: str, source_type: str = "referencia") -> int:
    """
    Carrega todos os documentos de um diretório, divide em chunks,
    gera embeddings e insere no ChromaDB.

    Args:
        directory: Caminho do diretório com os arquivos.
        source_type: 'referencia' (leis, decretos) ou 'exemplo' (modelos antigos).

    Returns:
        Número de chunks inseridos.
    """
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {directory}")

    all_docs: list[Document] = []
    supported_exts = {".pdf", ".docx", ".doc", ".txt"}

    for file_path in path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_exts:
            try:
                docs = _load_file(str(file_path))
                for doc in docs:
                    doc.metadata["source_file"] = file_path.name
                    doc.metadata["source_type"] = source_type
                all_docs.extend(docs)
            except Exception as e:
                print(f"[loader] Erro ao carregar {file_path.name}: {e}")

    if not all_docs:
        print(f"[loader] Nenhum documento encontrado em {directory}")
        return 0

    splitter = _get_splitter()
    chunks = splitter.split_documents(all_docs)

    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    print(
        f"[loader] {len(all_docs)} docs → {len(chunks)} chunks "
        f"inseridos no ChromaDB (coleção: {get_ai_config().chroma_collection_name})"
    )
    return len(chunks)


def ingest_all() -> dict[str, int]:
    """
    Varre os diretórios de referências e exemplos e popula o ChromaDB.

    Use este comando após adicionar novos documentos:
        python -c "from app.ai.loader import ingest_all; ingest_all()"
    """
    config = get_ai_config()
    resultados = {}

    for dir_path, label in [
        (config.referencias_dir, "referencias"),
        (config.exemplos_dir, "exemplos"),
    ]:
        count = ingest_directory(dir_path, source_type=label)
        resultados[label] = count

    return resultados
