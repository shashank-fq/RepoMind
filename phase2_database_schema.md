# RepoMind – Phase 2: Database Schema & Migrations

> **Status:** Ready to implement (Phase 1 ✅ complete)  
> **Goal:** Define all SQLAlchemy models, generate Alembic migrations, and seed a test record.

---

## Overview

Phase 1 gave us a running FastAPI app with a database connection and a `/health` endpoint.  
Phase 2 makes the database **useful** — every table we'll ever need is designed now, so later phases just start inserting data without any surprise schema changes.

---

## File Structure After Phase 2

```
repomind/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── __init__.py          ← export all models here
│   │   │   ├── user.py
│   │   │   ├── repository.py
│   │   │   ├── code_file.py
│   │   │   ├── code_chunk.py
│   │   │   ├── conversation.py
│   │   │   ├── test_run.py
│   │   │   ├── evaluation.py
│   │   │   └── request_log.py
│   │   └── ...
│   └── alembic/
│       └── versions/
│           └── 001_initial_schema.py   ← auto-generated
└── scripts/
    └── seed.py                          ← manual seed script
```

---

## Step-by-Step Implementation

### Step 1 – Enable pgvector Extension

Before defining models, the `vector` type must be available in Postgres.  
Add an Alembic migration to create the extension:

```python
# alembic/versions/000_enable_pgvector.py
from alembic import op

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

def downgrade():
    op.execute("DROP EXTENSION IF EXISTS vector")
```

Run this **first**, before any model migration.

---

### Step 2 – Define SQLAlchemy Models

All models inherit from `Base` (already defined in `database.py`).

#### `app/models/user.py`
```python
from datetime import datetime
import uuid
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

---

#### `app/models/repository.py`
```python
from datetime import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    github_url: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    versions: Mapped[list["RepositoryVersion"]] = relationship(back_populates="repository")


class RepositoryVersion(Base):
    __tablename__ = "repository_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"), nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # status values: pending | processing | ready | error
    cloned_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    repository: Mapped["Repository"] = relationship(back_populates="versions")
    code_files: Mapped[list["CodeFile"]] = relationship(back_populates="version")
```

---

#### `app/models/code_file.py`
```python
from datetime import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class CodeFile(Base):
    __tablename__ = "code_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repository_versions.id"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)       # relative path in repo
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    version: Mapped["RepositoryVersion"] = relationship(back_populates="code_files")
    chunks: Mapped[list["CodeChunk"]] = relationship(back_populates="file")
```

---

#### `app/models/code_chunk.py`  ← **the most important model**

This table holds every code unit we embed. The `embedding` column uses pgvector.

```python
from datetime import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.database import Base

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2; change to 1536 for OpenAI

class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("code_files.id"), nullable=False)

    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # e.g. "MyClass", "my_function", None for top-level code
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
    # nullable=True because embedding is generated in Phase 6 (after chunking)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    file: Mapped["CodeFile"] = relationship(back_populates="chunks")
```

> **Why nullable embedding?** Chunks are inserted first (Phase 5), then embeddings are
> filled in batch (Phase 6). This avoids blocking ingestion on embedding generation.

---

#### `app/models/conversation.py`
```python
from datetime import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # role: "user" | "assistant" | "tool"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
```

---

#### `app/models/test_run.py`
```python
from datetime import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repository_versions.id"), nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    results: Mapped[list["TestResult"]] = relationship(back_populates="run")


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_runs.id"), nullable=False)
    test_name: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    # outcome: "passed" | "failed" | "error" | "skipped"
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["TestRun"] = relationship(back_populates="results")
```

---

#### `app/models/evaluation.py`
```python
from datetime import datetime
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class EvalDatasetItem(Base):
    __tablename__ = "eval_dataset_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_files: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # e.g. ["auth/service.py", "models/user.py"]
    expected_lines: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. {"auth/service.py": [42, 68]}


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"), nullable=False)
    recall_at_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision_at_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    mrr: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

---

#### `app/models/request_log.py`
```python
from datetime import datetime
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieved_chunks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

---

#### `app/models/__init__.py`
```python
# Import all models so Alembic can detect them via Base.metadata
from app.models.user import User
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.models.conversation import Conversation, Message
from app.models.test_run import TestRun, TestResult
from app.models.evaluation import EvalDatasetItem, EvaluationRun
from app.models.request_log import RequestLog

__all__ = [
    "User",
    "Repository", "RepositoryVersion",
    "CodeFile",
    "CodeChunk",
    "Conversation", "Message",
    "TestRun", "TestResult",
    "EvalDatasetItem", "EvaluationRun",
    "RequestLog",
]
```

---

### Step 3 – Update `alembic/env.py`

Alembic needs to import your models so it can auto-detect schema changes.  
In `alembic/env.py`, add these two lines near the top:

```python
# alembic/env.py  (add these imports)
from app.database import Base
import app.models  # noqa – registers all models with Base.metadata

target_metadata = Base.metadata
```

This replaces the default `target_metadata = None`.

---

### Step 4 – Generate & Run the Migration

```bash
# In backend/ with venv active and DB running:
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

**Before running**, manually review the generated file in `alembic/versions/`. Check:
- All tables are listed in `upgrade()`.
- The `vector` column type appears correctly (`Vector(384)`).
- Foreign key ordering is correct (parent tables first).

---

### Step 5 – Seed a Test Repository Record

Create `scripts/seed.py`:

```python
"""
Seed a minimal Repository record for manual testing.
Run with: python -m scripts.seed
"""
import asyncio
import uuid
from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion

async def seed():
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=uuid.uuid4(),
            github_url="https://github.com/psf/requests",
            name="requests",
        )
        session.add(repo)
        await session.flush()

        version = RepositoryVersion(
            id=uuid.uuid4(),
            repository_id=repo.id,
            commit_hash="abc123",
            status="ready",
        )
        session.add(version)
        await session.commit()

        print(f"Seeded: Repository {repo.id}, Version {version.id}")

if __name__ == "__main__":
    asyncio.run(seed())
```

---

### Step 6 – Write a Test

Create `tests/test_schema.py`:

```python
"""
Verify that we can insert and query a repository + code chunk round-trip.
"""
import asyncio
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk


@pytest.mark.asyncio
async def test_repository_chunk_roundtrip():
    async with AsyncSessionLocal() as session:
        # 1. Create repo
        repo = Repository(github_url="https://github.com/test/test", name="test")
        session.add(repo)
        await session.flush()

        # 2. Create version
        version = RepositoryVersion(
            repository_id=repo.id, commit_hash="aaa000", status="ready"
        )
        session.add(version)
        await session.flush()

        # 3. Create file
        file = CodeFile(
            version_id=version.id,
            path="auth/service.py",
            language="python",
            content="def login(): pass",
        )
        session.add(file)
        await session.flush()

        # 4. Create chunk (no embedding yet)
        chunk = CodeChunk(
            file_id=file.id,
            start_line=1,
            end_line=1,
            symbol="login",
            language="python",
            content="def login(): pass",
        )
        session.add(chunk)
        await session.commit()

        # 5. Query it back
        from sqlalchemy import select
        result = await session.execute(
            select(CodeChunk).where(CodeChunk.symbol == "login")
        )
        fetched = result.scalars().first()

        assert fetched is not None
        assert fetched.content == "def login(): pass"
        assert fetched.start_line == 1
```

---

## Entity Relationship Overview

```
users
  └── repositories (user_id FK, nullable)
        └── repository_versions (repository_id FK)
              └── code_files (version_id FK)
                    └── code_chunks (file_id FK)  ← has embedding column

repositories
  └── conversations (repository_id FK)
        └── messages (conversation_id FK)
  └── eval_dataset_items (repository_id FK)
  └── evaluation_runs (repository_id FK)

repository_versions
  └── test_runs (version_id FK)
        └── test_results (run_id FK)

conversations
  └── request_logs (conversation_id FK, nullable)
```

---

## Checklist

- [ ] `app/models/user.py` created
- [ ] `app/models/repository.py` created (Repository + RepositoryVersion)
- [ ] `app/models/code_file.py` created
- [ ] `app/models/code_chunk.py` created with `Vector(384)` column
- [ ] `app/models/conversation.py` created (Conversation + Message)
- [ ] `app/models/test_run.py` created (TestRun + TestResult)
- [ ] `app/models/evaluation.py` created (EvalDatasetItem + EvaluationRun)
- [ ] `app/models/request_log.py` created
- [ ] `app/models/__init__.py` exports all models
- [ ] `alembic/env.py` updated with `target_metadata = Base.metadata`
- [ ] pgvector extension migration created and run first
- [ ] `alembic revision --autogenerate -m "initial schema"` run and reviewed
- [ ] `alembic upgrade head` run successfully
- [ ] `scripts/seed.py` created and run manually
- [ ] `tests/test_schema.py` written and passing

---

## Common Errors to Watch For

| Error | Cause | Fix |
|---|---|---|
| `sqlalchemy.exc.ProgrammingError: type "vector" does not exist` | pgvector extension not created | Run the `000_enable_pgvector` migration first |
| `ModuleNotFoundError: No module named 'pgvector'` | Missing dependency | `pip install pgvector` |
| Alembic generates empty migration | Models not imported in `env.py` | Add `import app.models` to `env.py` |
| `Foreign key constraint violation` during seed | Wrong table creation order | Alembic handles ordering automatically; re-run `upgrade head` |
| `Vector dimension mismatch` in Phase 6 | Embedding dim changed after schema creation | Create a new migration to alter the column dimension |

---

## What Phase 2 Achieves

By the end of this phase the database has **all tables** that every future phase will need.  
No more `ALTER TABLE` surprises mid-project. Phases 3–28 are purely about filling these tables with data.

**Next up → Phase 3:** Accept a GitHub URL, clone the repo with `gitpython`, and insert the first real `Repository` + `RepositoryVersion` rows.
