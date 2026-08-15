from fastapi import FastAPI
from sqlalchemy import text

from app.api import repositories_router
from app.database import AsyncSessionLocal

app = FastAPI(
    title="RepoMind",
    description="Automated Codebase Knowledge Graph & RAG System",
    version="0.3.0",
)

# Include API routers
app.include_router(repositories_router)


@app.get("/health", tags=["System"])
async def health():
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}