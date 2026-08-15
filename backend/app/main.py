from fastapi import FastAPI
from sqlalchemy import text

from app.database import AsyncSessionLocal


app = FastAPI(title="RepoMind")


@app.get("/health")
async def health():
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))

    return {"status": "ok"}