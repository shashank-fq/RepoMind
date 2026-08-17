from fastapi import FastAPI
from sqlalchemy import text

from app.api import repositories_router, files_router, chunks_router
from app.database import AsyncSessionLocal

app = FastAPI(
    title="RepoMind",
    description="Automated Codebase Knowledge Graph & RAG System",
    version="0.5.0",
)

# Include API routers
app.include_router(repositories_router)
app.include_router(files_router)
app.include_router(chunks_router)


@app.get("/health", tags=["System"])
async def health():
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}