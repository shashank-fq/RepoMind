from uuid import UUID
from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    """
    Request body schema for semantic vector search across code chunks.
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language search query or code snippet keywords",
        examples=["How is JWT user authentication validated?"]
    )
    repository_id: UUID | None = Field(
        default=None,
        description="Filter results by specific Repository ID. If omitted, searches latest ready version of target repo."
    )
    version_id: UUID | None = Field(
        default=None,
        description="Filter results by exact RepositoryVersion ID. Overrides repository_id lookup if provided."
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of code chunk results to return (1-100)"
    )
    min_similarity: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Minimum cosine similarity threshold (range: -1.0 to 1.0)"
    )
    language: str | None = Field(
        default=None,
        description="Filter search results by programming language (e.g. 'python', 'typescript')"
    )
    symbol_only: bool = Field(
        default=False,
        description="If True, only return chunks that contain an extracted symbol (class, function, method)"
    )

class SearchResultItem(BaseModel):
    """
    Individual code chunk match returned by vector search.
    """
    chunk_id: UUID
    file_id: UUID
    file_path: str = Field(..., description="Relative file path within repository", examples=["app/auth/jwt.py"])
    start_line: int = Field(..., description="Starting line number (1-indexed)")
    end_line: int = Field(..., description="Ending line number (1-indexed)")
    symbol: str | None = Field(None, description="Extracted symbol name (e.g. 'verify_token')")
    language: str = Field(..., description="Programming language of chunk")
    content: str = Field(..., description="Raw text snippet of code chunk")
    similarity_score: float = Field(..., description="Cosine similarity score (1.0 = identical, 0.0 = orthogonal)")
    distance: float = Field(..., description="Raw pgvector cosine distance (<=> operator value)")

class SearchResponse(BaseModel):
    """
    Full response container for semantic search queries.
    """
    query: str
    repository_id: UUID | None
    version_id: UUID | None
    total_results: int
    results: list[SearchResultItem]
    execution_time_ms: float = Field(..., description="Query execution and vector search duration in milliseconds")
    provider: str = Field(..., description="Embedding provider model name used for query vectorization")