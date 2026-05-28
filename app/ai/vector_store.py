from functools import lru_cache

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma

from app.ai.config import get_ai_config
from app.ai.embedding import get_embeddings


def _get_chroma_client() -> chromadb.PersistentClient:
    """
    Cria um cliente ChromaDB persistente em disco.

    ChromaDB armazena os vetores no diretório configurado em
    CHROMA_PERSIST_DIR. Não requer servidor separado — é uma
    biblioteca embutida que usa SQLite3 internamente.
    """
    config = get_ai_config()
    return chromadb.PersistentClient(
        path=config.chroma_persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )


def get_vector_store() -> Chroma:
    """
    Retorna o vector store LangChain wrapper do ChromaDB.

    Se a coleção ainda não existir (primeiro uso), o ChromaDB
    a cria automaticamente ao inserir documentos. O vector store
    usa o modelo de embeddings configurado para gerar vetores
    tanto na inserção quanto na busca.
    """
    config = get_ai_config()
    embeddings = get_embeddings()
    client = _get_chroma_client()

    return Chroma(
        client=client,
        collection_name=config.chroma_collection_name,
        embedding_function=embeddings,
    )


def get_collection_stats() -> dict:
    """Retorna estatísticas da coleção para diagnóstico."""
    store = get_vector_store()
    count = store._collection.count()
    return {
        "collection_name": get_ai_config().chroma_collection_name,
        "total_documents": count,
    }
