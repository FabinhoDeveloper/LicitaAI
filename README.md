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
| Backend | Python 3.12+, FastAPI |
| Banco de dados | MySQL 8.0 |
| ORM | SQLAlchemy 2.x |
| Frontend | Jinja2 (templates server-side) |
| Infraestrutura | Docker, Docker Compose |

---

## Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.12+

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/LicitAI.git
cd LicitAI

# 2. Crie o ambiente virtual
python -m venv venv
source venv/bin/activate

# 3. Instale as dependências
pip install fastapi uvicorn sqlalchemy jinja2 python-multipart pymysql

# 4. Suba o banco de dados
docker compose up -d
```

---

## Executando em desenvolvimento

```bash
# Ative o ambiente virtual
source venv/bin/activate

# Execute o servidor (com auto-reload)
python run.py
```

Acesse em `http://localhost:8000`

A documentação interativa da API estará disponível em `http://localhost:8000/docs`

---

## Estrutura do projeto

```
LicitAI/
├── app/
│   ├── main.py           # Entrada da aplicação FastAPI
│   ├── models/           # Modelos SQLAlchemy
│   ├── routes/           # Rotas da aplicação
│   ├── services/         # Lógica de negócio
│   ├── static/           # Arquivos estáticos (CSS, JS, imagens)
│   └── templates/        # Templates Jinja2
├── docker-compose.yaml   # Banco de dados MySQL
├── run.py                # Entrypoint do servidor uvicorn
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
