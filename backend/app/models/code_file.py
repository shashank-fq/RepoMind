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