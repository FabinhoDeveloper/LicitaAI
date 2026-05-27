# LicitAI

Ferramenta web para geração assistida por IA de documentos licitatórios municipais — DFD (Documento de Formalização da Demanda) e Termo de Referência — com base na Lei 14.133/2021.

Desenvolvido para uso interno da Prefeitura Municipal de Queluz-SP.

---

## Sobre o projeto

O LicitAI automatiza a redação das seções dissertativas de documentos de contratação pública. O servidor preenche os campos factuais via formulário, a IA gera o texto baseado em documentos reais e na legislação vigente, e o usuário revisa seção por seção antes de exportar o documento final em DOCX.

O sistema **não substitui a revisão humana**. Todo documento gerado é uma minuta que deve ser validada pelo responsável pela demanda antes de uso oficial.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x (async) |
| Banco de dados | PostgreSQL 16 + pgvector |
| IA / RAG | Anthropic API, LangChain, sentence-transformers |
| Exportação | python-docx-template |
| Frontend | React 18 + Vite + TypeScript |
| Infraestrutura | Docker, Docker Compose |

---

## Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.11+
- Node.js 18+
- Chave de API da Anthropic

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/LicitAI.git
cd LicitAI

# 2. Configure as variáveis de ambiente
cp backend/.env.example backend/.env
# edite o arquivo .env com suas credenciais

# 3. Suba o banco de dados
docker compose up -d

# 4. Instale as dependências do backend
cd backend
pip install -r requirements.txt

# 5. Execute as migrações
alembic upgrade head

# 6. Instale as dependências do frontend
cd ../frontend
npm install
```

---

## Executando em desenvolvimento

```bash
# Backend (na pasta /backend)
uvicorn app.main:app --reload --port 8000

# Frontend (na pasta /frontend)
npm run dev
```

Acesse em `http://localhost:5173`

A documentação da API estará disponível em `http://localhost:8000/docs`

---

## Estrutura do projeto

```
LicitAI/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   └── routes/
│   ├── alembic/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

---

## Documentos suportados

- **DFD** — Documento de Formalização da Demanda
- **Termo de Referência**

---

## Legislação de referência

- Lei Federal nº 14.133/2021 (Nova Lei de Licitações)
- Decreto Municipal nº 563/2026 — Queluz-SP

---

## Status

🚧 Em desenvolvimento