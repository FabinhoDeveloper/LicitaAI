from langchain_core.vectorstores import VectorStoreRetriever

from app.ai.config import get_ai_config
from app.ai.vector_store import get_vector_store


def get_retriever(
    search_kwargs: dict | None = None,
) -> VectorStoreRetriever:
    """
    Retorna um retriever configurado do LangChain que busca documentos
    relevantes no ChromaDB usando similaridade de cosseno.

    O retriever é usado pela chain RAG para recuperar os trechos mais
    relevantes dos documentos de referência antes de enviar ao LLM.

    Args:
        search_kwargs: Configuração adicional da busca.
            Ex: {"k": 10, "filter": {"source_type": "referencia"}}
            Se None, usa k=RAG_TOP_K do config.
    """
    config = get_ai_config()

    if search_kwargs is None:
        search_kwargs = {"k": config.rag_top_k}

    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs=search_kwargs)
