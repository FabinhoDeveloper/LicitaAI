from typing import Optional

from pydantic import BaseModel, Field


class DocumentoInput(BaseModel):
    """Dados que o usuário preenche no formulário web."""

    tipo_documento: str = Field(
        description="Tipo do documento: 'dfd' ou 'tr'"
    )
    titulo: str = Field(description="Título do documento")

    objeto: str = Field(description="Descrição do objeto da contratação")
    justificativa: str = Field(
        description="Justificativa da necessidade da contratação"
    )
    setor_demandante: str = Field(description="Setor que está demandando")

    valor_estimado: Optional[str] = Field(
        default=None,
        description="Valor estimado da contratação (ex: R$ 50.000,00)",
    )
    prazo_execucao: Optional[str] = Field(
        default=None, description="Prazo para execução (ex: 90 dias)"
    )
    modalidade: Optional[str] = Field(
        default=None,
        description="Modalidade sugerida (ex: pregão eletrônico, dispensa)",
    )
    observacoes: Optional[str] = Field(
        default=None,
        description="Informações complementares relevantes",
    )


class SecaoDocumento(BaseModel):
    """Uma seção individual do documento gerado."""

    titulo: str = Field(description="Título da seção")
    conteudo: str = Field(description="Conteúdo textual da seção")


class DocumentoOutput(BaseModel):
    """Resultado da geração pelo LLM."""

    tipo: str = Field(description="Tipo do documento gerado")
    titulo: str = Field(description="Título do documento")
    secoes: list[SecaoDocumento] = Field(
        description="Seções do documento geradas pelo LLM"
    )
    fontes_rag: list[str] = Field(
        default_factory=list,
        description="Fontes consultadas pelo RAG durante a geração",
    )
