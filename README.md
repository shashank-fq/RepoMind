# RepoMind 🧠⚡

![RepoMind Banner](./thumbnail.png)

> **Automated Codebase Knowledge Graph & Grounded RAG System with Precise Source Code Citations.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![pgvector](https://img.shields.io/badge/pgvector-Supported-blue?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

---

## 🌟 Overview

**RepoMind** is a high-performance, developer-focused Retrieval-Augmented Generation (RAG) backend engineered to understand, index, and query software codebases of any size. 

Unlike generic document RAG systems, RepoMind parses source code into **AST-aware logical symbols** (functions, classes, methods), vectorizes code structures into a high-dimensional vector space using **pgvector**, and generates strictly grounded answers backed by **automated `[file:line-range]` citations**.

---

## ✨ Key Features

- 🐙 **Automated Repository Ingestion**: Clone, validate, and version control any public or private GitHub repository seamlessly.
- 🌳 **AST-Aware Code Chunking**: Intelligently extracts class definitions, functions, and docstrings for Python while using an overlapping sliding-window fallback for non-Python source files.
- 🎯 **Ground-Truth Citations**: Answers are constrained by strict prompt boundaries; every technical statement includes an exact clickable or inspectable `[path/to/file.py:start_line-end_line]` source link.
- 🔌 **Swappable Vector Provider**: Built-in support for zero-cost local embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and OpenAI API embeddings (`text-embedding-3-small`).
- ⚡ **High-Performance Vector Storage**: Leverages PostgreSQL 16 with native `pgvector` cosine similarity search for sub-second retrieval over tens of thousands of code chunks.
- 🤖 **LLM Engine Integration**: Swappable LLM pipeline optimized for **DeepSeek-Chat** and **OpenAI GPT** models with low temperature strict factual enforcement.
- 🛡️ **Zero-Hallucination Guardrails**: Automatic fallbacks and strict contextual checks state when sufficient codebase evidence is absent.
- 🚀 **Production-Ready Async Architecture**: Built on FastAPI, SQLAlchemy 2.0 AsyncIO, Pydantic v2, Alembic schema migrations, and Docker Compose.

---

## 🏗️ Architecture Overview

```mermaid
flowchart TD
    subgraph Ingestion ["1. Ingestion & Preprocessing"]
        A["GitHub Repository URL"] -->|Git Clone & SHA Check| B["File Processor"]
        B -->|Filter ignored dirs & check size| C["Source Code Files"]
    end

    subgraph Chunking ["2. Code Parsing & Chunking"]
        C -->|Python AST Parser| D["AST Symbol Chunks"]
        C -->|Fallback Splitter| E["Line Window Chunks"]
    end

    subgraph Vectorization ["3. Vector Embedding"]
        D & E -->|Batch Processing| F["Embedding Provider Engine"]
        F -->|Local MiniLM / OpenAI| G[("(PostgreSQL + pgvector)")]
    end

    subgraph RAG Pipeline ["4. Retrieval & Grounded Synthesis"]
        H["User Natural Language Question"] -->|Embed Query| I["Vector Similarity Search"]
        G -->|Fetch Top-K Chunks| I
        I -->|Structured Context + System Guardrails| J["LLM - DeepSeek / OpenAI"]
        J -->|Generate Response| K["Citation Extractor & Verifier"]
        K --> L["Final Answer with [file:line-range] References"]
    end
```

---

## 🛠️ Tech Stack

- **Language & Framework**: Python 3.11+, [FastAPI](https://fastapi.tiangolo.com/)
- **Database & Storage**: PostgreSQL 16, [`pgvector`](https://github.com/pgvector/pgvector), [SQLAlchemy 2.0 (Async)](https://docs.sqlalchemy.org/)
- **Migrations & Schemas**: [Alembic](https://alembic.sqlalchemy.org/), [Pydantic v2](https://docs.pydantic.dev/)
- **Embeddings & ML**: [`sentence-transformers`](https://www.sbert.net/) (`all-MiniLM-L6-v2`), OpenAI Embeddings API
- **LLM Integration**: [OpenAI Python SDK](https://github.com/openai/openai-python), DeepSeek API
- **Version Control & Ingestion**: [GitPython](https://gitpython.readthedocs.io/)
- **Containerization & Testing**: Docker, Docker Compose, `pytest`, `pytest-asyncio`

---

## 📁 Repository Structure

```
understand/
├── backend/
│   ├── alembic/                # Database migration revisions
│   ├── app/
│   │   ├── api/                # FastAPI routers (repositories, files, chunks, embeddings, search, RAG)
│   │   ├── models/             # SQLAlchemy ORM models (Repository, Version, File, Chunk)
│   │   ├── schemas/            # Pydantic validation models
│   │   ├── services/           # Core domain logic
│   │   │   ├── chunker/        # AST & fallback line splitters
│   │   │   ├── embeddings/     # Swappable embedding provider abstraction
│   │   │   ├── file_processor.py # File scanner & cleaner
│   │   │   ├── ingestion.py    # Git repository cloning service
│   │   │   ├── search_service.py # Vector similarity search engine
│   │   │   └── rag_service.py  # Grounded RAG answer generator & citation parser
│   │   ├── config.py           # Application settings & env configuration
│   │   ├── database.py         # Async database connection session lifecycle
│   │   └── main.py             # FastAPI entry point
│   ├── tests/                  # Unit and integration test suite
│   ├── Dockerfile              # Backend service dockerfile
│   └── alembic.ini             # Alembic migration configuration
├── storage/                    # Local storage repository cache
├── docker-compose.yml          # PostgreSQL + pgvector database stack
├── plan.txt                    # Project master plan & feature roadmap
└── README.md                   # Project documentation
```

---

## 🚀 Quick Start Guide

### Prerequisites

- **Python**: `3.11` or higher
- **Docker & Docker Compose**: Installed and running
- **Git**: Installed locally

### 1. Clone the Repository & Configure Environment

```bash
git clone https://github.com/shashank-fq/RepoMind.git
cd understand

# Create and activate a Python virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql+asyncpg://repomind:repomind@localhost:5433/repomind
EMBEDDING_PROVIDER=local
OPENAI_API_KEY=your_openai_or_deepseek_api_key
```

### 2. Start Database Container

Launch PostgreSQL with `pgvector` enabled using Docker Compose:

```bash
docker compose up -d
```

### 3. Run Database Migrations

Apply Alembic migrations to set up the database schema:

```bash
cd backend
alembic upgrade head
```

### 4. Run the Backend API Server

Start the FastAPI application:

```bash
uvicorn app.main:app --reload --port 8000
```

The server will start at `http://localhost:8000`. You can test health by visiting `http://localhost:8000/health`.

---

## 📖 API Usage & Endpoints

Interactive Swagger UI documentation is available at `http://localhost:8000/docs`.

### 1. Ingest a GitHub Repository

```bash
curl -X POST "http://localhost:8000/repositories" \
     -H "Content-Type: application/json" \
     -d '{
           "github_url": "https://github.com/fastapi/fastapi",
           "branch": "main"
         }'
```

### 2. Generate Embeddings for Ingested Repo

```bash
curl -X POST "http://localhost:8000/repositories/{repository_id}/embeddings"
```

### 3. Semantic Vector Search

```bash
curl -X POST "http://localhost:8000/repositories/{repository_id}/search" \
     -H "Content-Type: application/json" \
     -d '{
           "query": "How is authentication handled in routing?",
           "top_k": 5
         }'
```

### 4. Grounded RAG Query (Q&A with Citations)

```bash
curl -X POST "http://localhost:8000/repositories/{repository_id}/ask" \
     -H "Content-Type: application/json" \
     -d '{
           "question": "Explain how the request middleware processes incoming requests.",
           "top_k": 5
         }'
```

**Example Response:**
```json
{
  "repository_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "version_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "question": "Explain how the request middleware processes incoming requests.",
  "answer": "Middleware processing begins by wrapping the core HTTP handler [fastapi/middleware/asynclib.py:20-45]. Incoming requests pass through each middleware layer sequentially before invoking route handlers.",
  "citations": [
    {
      "file_path": "fastapi/middleware/asynclib.py",
      "start_line": 20,
      "end_line": 45,
      "symbol": "AsyncMiddleware.dispatch",
      "snippet": "async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:\n    ..."
    }
  ],
  "retrieved_chunks_count": 5,
  "generation_time_ms": 420.5
}
```

---

## 🧪 Running Tests

RepoMind includes automated unit and integration test suites:

```bash
cd backend
pytest
```

To run test coverage report:

```bash
pytest --cov=app tests/
```

---

## 🗺️ Project Roadmap

- [x] **Phase 1-2**: Foundation, Schema Design & Alembic Migrations
- [x] **Phase 3-4**: GitHub Repository Ingestion & File Filtering
- [x] **Phase 5**: AST-Aware Python Code Chunking & Fallback Windowing
- [x] **Phase 6**: Swappable Vector Embedding Engine (`sentence-transformers` & OpenAI)
- [x] **Phase 7**: High-Precision Semantic Search via PostgreSQL `pgvector`
- [x] **Phase 8**: Grounded RAG Answer Generation & Automated Citation Engine
- [ ] **Phase 13**: Hybrid Search (Postgres Full-Text Search + Vector Similarity)
- [ ] **Phase 15-16**: Agentic Tool Loop (`search_code`, `read_file`, `git_history`)
- [ ] **Phase 20-21**: Automated Evaluation Pipeline (Recall@K, Precision@K, LLM-as-a-Judge)
- [ ] **Phase 23**: Web Analytics Dashboard & Interactive Code Explorer UI

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
