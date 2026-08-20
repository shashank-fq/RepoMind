from uuid import UUID
from pydantic import BaseModel

class EmbeddingStatusResponse(BaseModel):
    repository_id: UUID
    version_id: UUID
    status: str
    total_chunks: int
    embedded_chunks: int
    embedding_dimension: int
    provider: str

class EmbeddingTriggerResponse(BaseModel):
    repository_id: UUID
    version_id: UUID
    message: str
    status: str