from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.ai.config import get_ai_config
from app.ai.prompts import get_prompts_for_type
from app.ai.retriever import get_retriever


def _build_llm() -> ChatOpenAI:
    """
    Constrói o cliente DeepSeek via interface OpenAI-compatível.

    A API do DeepSeek é compatível com o formato OpenAI, então o
    ChatOpenAI do LangChain funciona diretamente, bastando apontar
    o base_url para api.deepseek.com.
    """
    config = get_ai_config()
    return ChatOpenAI(
        model=config.deepseek_model,
        base_url=config.deepseek_base_url,
        api_key=config.deepseek_api_key,
        temperature=config.llm_temperature,
        max_tokens=config.llm_max_tokens,
    )


def _format_docs(docs) -> str:
    """Formata a lista de documentos recuperados em uma string para o prompt."""
    if not docs:
        return "Nenhum documento relevante encontrado."

    partes = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source_file", "desconhecido")
        partes.append(f"[Fonte {i}: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(partes)


def _get_source_files(docs) -> list[str]:
    """Extrai os nomes dos arquivos fonte dos documentos recuperados."""
    sources = set()
    for doc in docs:
        source = doc.metadata.get("source_file", "desconhecido")
        sources.add(source)
    return sorted(sources)


def create_rag_chain(tipo_documento: str):
    """
    Cria a chain RAG completa para um tipo de documento.

    A chain executa o seguinte pipeline:
    1. Converte o input do usuário em query de busca
    2. Recupera documentos relevantes do ChromaDB (RAG)
    3. Formata o prompt com contexto recuperado + dados do usuário
    4. Envia para o LLM (DeepSeek)
    5. Extrai o texto da resposta

    Args:
        tipo_documento: 'dfd' ou 'tr'

    Returns:
        Uma chain LangChain executável com .invoke(input_dict)
    """
    system_prompt, user_prompt = get_prompts_for_type(tipo_documento)
    llm = _build_llm()
    retriever = get_retriever()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
    )

    def combine_input(input_dict: dict) -> dict:
        """
        Combina os campos do formulário em uma query semântica
        para maximizar a relevância da busca no ChromaDB.
        """
        query = (
            f"{input_dict.get('objeto', '')} "
            f"{input_dict.get('justificativa', '')} "
            f"{input_dict.get('modalidade', '')} "
            f"{input_dict.get('tipo_documento', '')}"
        )
        input_dict["query"] = query
        return input_dict

    chain = (
        RunnablePassthrough.assign(context=lambda x: _format_docs(
            retriever.invoke(x["query"])
        ))
        | RunnablePassthrough.assign(fontes=lambda x: _get_source_files(
            retriever.invoke(x["query"])
        ))
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def create_dfd_chain():
    """Retorna a chain RAG para geração de DFD."""
    return create_rag_chain("dfd")


def create_tr_chain():
    """Retorna a chain RAG para geração de Termo de Referência."""
    return create_rag_chain("tr")


def generate_document(tipo: str, dados: dict) -> dict:
    """
    Gera um documento completo via RAG + LLM.

    Args:
        tipo: 'dfd' ou 'tr'
        dados: Dicionário com os campos do formulário
            (objeto, justificativa, setor_demandante, valor_estimado,
             prazo_execucao, modalidade, observacoes)

    Returns:
        Dict com:
            - texto: string com o documento gerado
            - fontes: lista de arquivos fonte consultados
    """
    config = get_ai_config()
    system_prompt, user_prompt = get_prompts_for_type(tipo)
    llm = _build_llm()
    retriever = get_retriever()

    dados_completos = {
        "tipo_documento": tipo,
        "objeto": dados.get("objeto", "Não informado"),
        "justificativa": dados.get("justificativa", "Não informado"),
        "setor_demandante": dados.get("setor_demandante", "Não informado"),
        "valor_estimado": dados.get("valor_estimado", "Não informado"),
        "prazo_execucao": dados.get("prazo_execucao", "Não informado"),
        "modalidade": dados.get("modalidade", "Não informada"),
        "observacoes": dados.get("observacoes", "Nenhuma"),
    }

    query = (
        f"{dados_completos['objeto']} "
        f"{dados_completos['justificativa']} "
        f"{dados_completos['modalidade']}"
    )
    docs = retriever.invoke(query)
    fontes = _get_source_files(docs)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
    )

    chain = prompt | llm | StrOutputParser()
    texto = chain.invoke({**dados_completos, "context": _format_docs(docs)})

    return {
        "texto": texto,
        "fontes": fontes,
    }
