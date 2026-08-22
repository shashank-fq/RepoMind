from uuid import UUID
from pydantic import BaseModel, Field

class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000, description="Natural language question about the codebase")
    language: str | None = Field(None, description="Optional programming language filter (e.g. python, typescript)")
    path_pattern: str | None = Field(None, description="Optional file path substring filter (e.g. services/auth)")
    top_k: int = Field(5, ge=1, le=20, description="Number of relevant code chunks to retrieve for LLM context")
    min_similarity: float = Field(0.2, ge=0.0, le=1.0, description="Minimum vector similarity threshold for context chunks")

class Citation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    symbol: str | None = None
    snippet: str

class RAGResponse(BaseModel):
    repository_id: UUID
    version_id: UUID
    question: str
    answer: str
    citations: list[Citation]
    retrieved_chunks_count: int
    generation_time_ms: float