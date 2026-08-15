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