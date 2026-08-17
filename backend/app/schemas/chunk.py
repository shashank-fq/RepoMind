from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class CodeChunkResponse(BaseModel):
    id: UUID
    file_id: UUID
    start_line: int
    end_line: int
    symbol: str | None
    language: str
    content: str
    has_embedding: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CodeChunkPaginatedResponse(BaseModel):
    total_chunks: int
    page: int
    page_size: int
    chunks: list[CodeChunkResponse]