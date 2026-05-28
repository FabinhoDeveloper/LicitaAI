# Arquitetura de IA — LicitAI

Documentação da camada de inteligência artificial do LicitAI: como a aplicação se comunica com o LLM, como funciona o RAG e o que cada arquivo faz.

---

## Visão geral

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUÁRIO (navegador)                      │
│  Preenche formulário com dados do projeto (objeto, justificativa,│
│  valor, modalidade, etc.)                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI (app/routes/ai_routes.py)             │
│  POST /documentos/gerar                                         │
│  Recebe formulário → chama ai_service.generate()                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              app/services/ai_service.py (orquestrador)           │
│  1. Valida entrada (Pydantic)                                   │
│  2. Monta query semântica                                       │
│  3. Chama generate_document()                                   │
│  4. Retorna texto + fontes                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   app/ai/chains.py  (RAG Chain)                  │
│                                                                  │
│  query ──► Retriever ──► ChromaDB ──► chunks relevantes         │
│                  │                                               │
│                  ▼                                               │
│        prompt = system_prompt + context(chunks) + user_data      │
│                  │                                               │
│                  ▼                                               │
│           DeepSeek API (LLM) ──► texto gerado                    │
│                  │                                               │
│                  ▼                                               │
│            resultado: { texto, fontes }                          │
└─────────────────────────────────────────────────────────────────┘
```

### O que é RAG (Retrieval-Augmented Generation)?

RAG é a técnica de **recuperar informações relevantes** de uma base de conhecimento **antes** de enviar o prompt para o LLM. Isso faz o modelo gerar respostas embasadas em fatos reais, em vez de "alucinar" conteúdo.

No LicitAI, as etapas são:
1. **Indexação**: Documentos de referência (leis, decretos, modelos antigos) são divididos em pedaços (chunks), transformados em vetores numéricos (embeddings) e armazenados no ChromaDB.
2. **Recuperação**: Quando o usuário submete dados de um novo projeto, o sistema converte a consulta em vetor e busca os chunks mais similares no ChromaDB.
3. **Geração**: Os chunks recuperados são injetados no prompt junto com os dados do usuário. O LLM gera o texto usando o contexto real como base.

---

## Estrutura de diretórios

```
app/
├── ai/                          ← Camada de IA (TUDO NOVO)
│   ├── __init__.py              # Reexporta funções principais
│   ├── config.py                # Configuração central (env vars → dataclass)
│   ├── embedding.py             # Modelo de embeddings (sentence-transformers)
│   ├── vector_store.py          # Cliente ChromaDB (banco vetorial)
│   ├── loader.py                # Pipeline de ingestão de documentos
│   ├── prompts.py               # Templates de prompt (DFD e TR)
│   ├── retriever.py             # LangChain retriever (busca no ChromaDB)
│   ├── chains.py                # Chains RAG completas + generate_document()
│   └── schemas.py               # Schemas Pydantic (entrada/saída)
│
├── data/                        ← Dados de IA (TUDO NOVO)
│   ├── referencias/             # PDFs/DOCXs: leis, decretos, jurisprudência
│   ├── exemplos/                # PDFs/DOCXs: modelos antigos de ETP/DFD/TR
│   └── chroma_db/               # Persistência do ChromaDB (gerado automaticamente)
│
├── services/
│   └── ai_service.py            ← NOVO: orquestra geração (a ser criado)
│
└── routes/
    └── ai_routes.py             ← NOVO: endpoints /documentos/gerar, etc. (a ser criado)
```

---

## Descrição de cada arquivo

### `app/ai/config.py` — Configuração central

```python
@dataclass
class AIConfig:
    deepseek_api_key: str        # Chave da API DeepSeek
    deepseek_base_url: str       # URL base (padrão: api.deepseek.com/v1)
    deepseek_model: str          # Modelo (padrão: deepseek-chat)
    llm_temperature: float       # Temperatura (0.3 = conservador)
    llm_max_tokens: int          # Máximo de tokens na resposta
    embedding_model_name: str    # Modelo sentence-transformers
    embedding_device: str        # "cpu" ou "cuda"
    chroma_persist_dir: str      # Onde salvar o ChromaDB
    chroma_collection_name: str  # Nome da coleção
    rag_top_k: int               # Quantos chunks recuperar na busca
    chunk_size: int              # Tamanho dos chunks
    chunk_overlap: int           # Sobreposição entre chunks
    referencias_dir: str         # Diretório de leis/decretos
    exemplos_dir: str            # Diretório de modelos antigos
```

Todas as variáveis podem ser sobrescritas via `.env`. Ver `.env.example` para a lista completa.

### `app/ai/embedding.py` — Modelo de embeddings

Centraliza a instância do modelo de embeddings local.

- Usa **sentence-transformers** via `langchain_huggingface.HuggingFaceEmbeddings`
- Modelo padrão: `intfloat/multilingual-e5-large` (1024 dimensões, otimizado para português e outras línguas)
- O modelo é carregado **uma única vez** (cache com `@lru_cache`) e fica em memória
- Na primeira execução, faz download do modelo (~2 GB). As execuções seguintes usam o cache local

Por que modelo local e não API (OpenAI embeddings)?
- Zero custo operacional após o download inicial
- Independência de internet para gerar embeddings
- Privacidade: os documentos não saem da máquina

### `app/ai/vector_store.py` — ChromaDB

Cliente do banco de dados vetorial ChromaDB.

- ChromaDB é um banco **embutido** (não requer servidor separado — é uma biblioteca Python que usa SQLite internamente)
- Armazena os vetores em `app/data/chroma_db/` (diretório no `.gitignore`)
- A função `get_vector_store()` retorna um wrapper LangChain (`langchain_chroma.Chroma`) que expõe métodos como `add_documents()`, `similarity_search()`, etc.
- Se a coleção não existir, é criada automaticamente ao inserir o primeiro documento

### `app/ai/loader.py` — Ingestão de documentos

Pipeline de indexação: transforma arquivos brutos em vetores pesquisáveis.

Fluxo:
1. Varre os diretórios `referencias/` e `exemplos/`
2. Para cada arquivo (PDF, DOCX, TXT), usa o loader apropriado do LangChain
3. Divide o texto em chunks com `RecursiveCharacterTextSplitter` (1000 caracteres, overlap 200)
4. Gera embeddings via `HuggingFaceEmbeddings`
5. Insere os chunks no ChromaDB com metadados (nome do arquivo, tipo de fonte)

Para executar a ingestão:
```bash
source venv/bin/activate
python -c "from app.ai.loader import ingest_all; print(ingest_all())"
```

### `app/ai/prompts.py` — Templates de prompt

Contém os prompts para cada tipo de documento. Cada tipo tem dois prompts:

- **System prompt**: Define o papel do LLM (especialista em licitações), as regras obrigatórias e o estilo de escrita
- **User prompt**: Template preenchido com os dados do formulário. A variável `{context}` é preenchida pelo RAG com os chunks recuperados

Tipos disponíveis:
- `DFD` — Documento de Formalização da Demanda (6 seções)
- `TR` — Termo de Referência (10 seções)

Cada prompt instrui o LLM a:
- Citar artigos da Lei 14.133/2021
- Seguir estrutura padronizada de seções
- Não inventar dados (usar apenas os fornecidos + contexto)

### `app/ai/retriever.py` — Busca no ChromaDB

Cria um `VectorStoreRetriever` do LangChain que:
- Recebe uma query textual
- Gera o embedding da query (via mesmo modelo usado na ingestão)
- Busca os `k` chunks mais similares no ChromaDB (por similaridade de cosseno)
- Retorna uma lista de `Document` LangChain

### `app/ai/chains.py` — Chains RAG

Onde acontece a "mágica". Duas funções principais:

**`create_rag_chain(tipo)`** — Constrói uma chain LangChain reutilizável:
```
input → retriever busca docs → formata contexto → preenche prompt → LLM → extrai texto
```

**`generate_document(tipo, dados)`** — Função de alto nível para uso nos serviços:
1. Monta a query semântica a partir dos dados do formulário
2. Busca documentos relevantes no ChromaDB
3. Formata o prompt (system + contexto recuperado + dados do usuário)
4. Envia para o DeepSeek
5. Retorna `{ texto, fontes }`

**Modelo LLM**: DeepSeek-V3 via API compatível com OpenAI. A classe `ChatOpenAI` do LangChain funciona diretamente, bastando apontar `base_url` para `https://api.deepseek.com/v1`.

### `app/ai/schemas.py` — Schemas Pydantic

Define a estrutura dos dados que entram e saem da camada de IA:

- **`DocumentoInput`**: Campos que o usuário preenche no formulário (objeto, justificativa, setor, valor, prazo, modalidade, observações)
- **`DocumentoOutput`**: Estrutura do documento gerado (tipo, título, lista de seções, fontes consultadas)
- **`SecaoDocumento`**: Uma seção individual do documento (título + conteúdo)

---

## Documentos de referência: onde colocar cada tipo

Os documentos que alimentam o RAG ficam em dois diretórios. A separação não é cosmética — cada diretório gera um metadado `source_type` diferente nos chunks, permitindo filtrar buscas depois.

### `app/data/referencias/` — Embasamento legal e técnico

Documentos que fornecem a **base jurídica e doutrinária** para o LLM fundamentar as respostas:

| Tipo | Exemplos de arquivo |
|---|---|
| Legislação federal | `lei-14133-2021.pdf` (texto integral da Nova Lei de Licitações) |
| Legislação municipal | `decreto-563-2026.pdf` (Decreto Municipal de Queluz-SP) |
| Manuais técnicos | `manual-TCE-SP.pdf` (instruções do Tribunal de Contas) |
| Doutrina | `artigo-dispensa-14133.pdf` (artigos sobre pontos polêmicos da lei) |
| Jurisprudência | `jurisprudencia-TCU.pdf` (decisões relevantes do TCU) |
| Normas complementares | `IN-SEGES-05-2017.pdf` (instruções normativas aplicáveis) |

**Objetivo na geração**: esses chunks aparecem no prompt como `[Fonte: lei-14133-2021.pdf]` e o LLM extrai deles os artigos corretos para citar.

### `app/data/exemplos/` — Modelos de referência

Documentos que fornecem o **estilo, estrutura e linguagem** de documentos já aprovados:

| Tipo | Exemplos de arquivo |
|---|---|
| DFD antigos | `dfd-secretaria-educacao-2024.docx` |
| TR antigos | `tr-aquisicao-notebooks-2023.docx` |
| ETP antigos | `etp-reforma-predio-2024.docx` |
| Qualquer documento já finalizado e aprovado pela prefeitura | `.pdf` ou `.docx` |

**Objetivo na geração**: o LLM usa esses exemplos como referência de tom, formatação e nível de detalhe esperado pela administração municipal.

### Formato dos arquivos

Formatos aceitos: **PDF**, **DOCX**, **TXT**. Outros formatos são ignorados silenciosamente.

### Metadados e filtro

Cada chunk recebe automaticamente um metadado `source_type` durante a ingestão (`app/ai/loader.py:44-45`). Isso permite filtrar a busca:

```python
from app.ai.retriever import get_retriever

# Buscar APENAS leis (ignora exemplos)
retriever = get_retriever(search_kwargs={
    "k": 5,
    "filter": {"source_type": "referencia"}
})

# Buscar APENAS modelos antigos
retriever = get_retriever(search_kwargs={
    "k": 3,
    "filter": {"source_type": "exemplo"}
})

# Padrão: busca em ambos (sem filtro)
retriever = get_retriever()
```

---

## Ingestão de documentos (embedding no ChromaDB)

A ingestão **não é automática** — é um passo manual executado sob demanda.

### Quando executar

- **Primeira vez**: após colocar os arquivos em `referencias/` e `exemplos/`
- **Depois**: sempre que adicionar, remover ou substituir um arquivo nesses diretórios
- **Não precisa**: a cada geração de documento — o RAG já busca automaticamente

### Como executar

```bash
source venv/bin/activate
python -c "from app.ai.loader import ingest_all; print(ingest_all())"
```

### O que acontece internamente

```
Para cada arquivo em referencias/ e exemplos/:
  1. PyPDFLoader / Docx2txtLoader / TextLoader → extrai texto bruto
  2. RecursiveCharacterTextSplitter → divide em chunks de ~1000 caracteres
  3. HuggingFaceEmbeddings → gera vetor numérico (1024 dimensões)
  4. ChromaDB → armazena chunk + vetor + metadados
```

Os dados ficam persistidos em `app/data/chroma_db/` (diretório no `.gitignore`). O ChromaDB usa SQLite internamente, sem servidor separado.

### Verificar se a ingestão funcionou

```python
from app.ai.vector_store import get_collection_stats
print(get_collection_stats())
# Exemplo de saída: {'collection_name': 'licitai_docs', 'total_documents': 247}
```

### Reindexar do zero

Se precisar limpar tudo e começar de novo (ex: mudou o chunk_size, trocou o modelo de embedding):

```bash
rm -rf app/data/chroma_db/
# Depois execute a ingestão novamente
python -c "from app.ai.loader import ingest_all; print(ingest_all())"
```

---

## Fluxo detalhado de geração de documento

### 1. Indexação (setup inicial, executado manualmente quando necessário)

```
PDF "lei-14133.pdf" ──► PyPDFLoader ──► texto bruto
                                              │
                              RecursiveCharacterTextSplitter
                              (chunk_size=1000, overlap=200)
                                              │
                                              ▼
                              [chunk1, chunk2, ..., chunkN]
                                              │
                              HuggingFaceEmbeddings
                              (multilingual-e5-large)
                                              │
                                              ▼
                              ChromaDB (app/data/chroma_db/)
```

### 2. Geração (executado a cada requisição)

```
Usuário preenche form:
  objeto = "Aquisição de notebooks para o setor de educação"
  justificativa = "Necessidade de modernizar equipamentos..."
  setor = "Secretaria Municipal de Educação"
  valor = "R$ 120.000,00"
  modalidade = "pregão eletrônico"
                    │
                    ▼
Query semântica:
  "Aquisição de notebooks setor educação necessidade modernizar
   equipamentos pregão eletrônico"
                    │
                    ▼
ChromaDB busca top_k=5 chunks similares
                    │
                    ▼
Chunks recuperados (exemplos):
  [Fonte 1: lei-14133.pdf]
  "Art. 28. São modalidades de licitação: I - pregão; ..."

  [Fonte 2: dfd-modelo-2024.docx]
  "DESCRIÇÃO DA NECESSIDADE: A Secretaria Municipal de Educação..."

  [Fonte 3: decreto-563.pdf]
  "Art. 5º As contratações de bens de informática deverão observar..."
                    │
                    ▼
Prompt final enviado ao DeepSeek:
  ┌─────────────────────────────────────────────┐
  │ SYSTEM: "Você é um especialista em..."       │
  │                                              │
  │ CONTEXT: [chunks recuperados formatados]     │
  │                                              │
  │ USER: "Dados do projeto:                     │
  │   Objeto: Aquisição de notebooks...          │
  │   ...                                        │
  │   Redija o DFD com as seguintes seções:      │
  │   1. Descrição da necessidade..."             │
  └─────────────────────────────────────────────┘
                    │
                    ▼
DeepSeek API retorna texto estruturado
                    │
                    ▼
Resposta:
  {
    "texto": "**1. Descrição da necessidade** ... (art. 14, Lei 14.133/2021)",
    "fontes": ["lei-14133.pdf", "dfd-modelo-2024.docx", "decreto-563.pdf"]
  }
```

---

## Configuração do ambiente (`.env`)

```env
# ==================== DeepSeek (LLM) ====================
DEEPSEEK_API_KEY=sk-sua-chave-aqui
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4096

# ==================== Embeddings (sentence-transformers) ====================
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-large
EMBEDDING_DEVICE=cpu

# ==================== ChromaDB ====================
CHROMA_PERSIST_DIR=app/data/chroma_db
CHROMA_COLLECTION_NAME=licitai_docs

# ==================== RAG ====================
RAG_TOP_K=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

---

## Dependências necessárias

```bash
pip install chromadb langchain-openai langchain-huggingface \
            langchain-chroma langchain-community langchain-text-splitters \
            sentence-transformers
```

---

## Como testar

### 1. Verificar se a configuração está correta:

```python
from app.ai.config import get_ai_config
config = get_ai_config()
print(config.deepseek_model)  # deepseek-chat
print(config.chroma_collection_name)  # licitai_docs
```

### 2. Indexar documentos de referência:

Siga as instruções da seção [Ingestão de documentos](#ingestão-de-documentos-embedding-no-chromadb) acima.

### 3. Verificar o que foi indexado:

```python
from app.ai.vector_store import get_collection_stats
print(get_collection_stats())
```

### 4. Gerar um documento de teste:

```python
from app.ai.chains import generate_document

resultado = generate_document("dfd", {
    "objeto": "Aquisição de notebooks para o setor de educação",
    "justificativa": "Necessidade de modernizar equipamentos defasados",
    "setor_demandante": "Secretaria Municipal de Educação",
    "valor_estimado": "R$ 120.000,00",
    "modalidade": "pregão eletrônico",
})

print(resultado["texto"])
print("\nFontes consultadas:", resultado["fontes"])
```

---

## Próximos passos (a implementar)

- [ ] **`app/services/ai_service.py`** — Orquestrador que valida a entrada, chama `generate_document()` e processa o resultado
- [ ] **`app/routes/ai_routes.py`** — Endpoint `POST /documentos/gerar` que recebe formulário e chama o serviço
- [ ] **Formulário HTML** — Interface web para o usuário preencher os dados do projeto
- [ ] **Página de resultado** — Exibe seções geradas para revisão antes da exportação
- [ ] **Exportação DOCX** — Geração de arquivo `.docx` com `python-docx`
- [ ] **Modelo ETP** — Prompt para Estudo Técnico Preliminar
