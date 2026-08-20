from app.api.repositories import router as repositories_router
from app.api.files import router as files_router
from app.api.chunks import router as chunks_router
from app.api.embeddings import router as embeddings_router

__all__ = ["repositories_router", "files_router", "chunks_router", "embeddings_router"]