from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.ai.config import get_ai_config


@lru_cache
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Retorna o modelo de embeddings local via sentence-transformers.

    Usa lru_cache para carregar o modelo apenas uma vez durante
    a vida da aplicação, evitando recarregar o modelo pesado
    (tipicamente 1-2 GB) a cada requisição.
    """
    config = get_ai_config()
    return HuggingFaceEmbeddings(
        model_name=config.embedding_model_name,
        model_kwargs={"device": config.embedding_device},
        encode_kwargs={"normalize_embeddings": True},
    )
