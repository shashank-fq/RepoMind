from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.repository import RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.schemas.embedding import EmbeddingStatusResponse, EmbeddingTriggerResponse
from app.services.embeddings import get_embedding_provider, process_version_embeddings

router = APIRouter(prefix="/repositories", tags=["Embeddings"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get(
    "/{repository_id}/embeddings/status",
    response_model=EmbeddingStatusResponse,
    summary="Get embedding generation status for a repository",
)
async def get_embeddings_status(repository_id: UUID, db: AsyncSession = Depends(get_db)):
    v_stmt = (
        select(RepositoryVersion)
        .where(RepositoryVersion.repository_id == repository_id)
        .order_by(RepositoryVersion.created_at.desc())
    )
    res = await db.execute(v_stmt)
    latest_version = res.scalars().first()

    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    # Subquery for file IDs
    file_ids_query = select(CodeFile.id).where(CodeFile.version_id == latest_version.id)

    # Total chunks
    tot_stmt = select(func.count(CodeChunk.id)).where(CodeChunk.file_id.in_(file_ids_query))
    tot_res = await db.execute(tot_stmt)
    total_chunks = tot_res.scalar_one() or 0

    # Embedded chunks
    emb_stmt = (
        select(func.count(CodeChunk.id))
        .where(CodeChunk.file_id.in_(file_ids_query))
        .where(CodeChunk.embedding.is_not(None))
    )
    emb_res = await db.execute(emb_stmt)
    embedded_chunks = emb_res.scalar_one() or 0

    provider = get_embedding_provider()

    return EmbeddingStatusResponse(
        repository_id=repository_id,
        version_id=latest_version.id,
        status=latest_version.status,
        total_chunks=total_chunks,
        embedded_chunks=embedded_chunks,
        embedding_dimension=provider.dimension,
        provider=provider.__class__.__name__,
    )


@router.post(
    "/{repository_id}/embed",
    response_model=EmbeddingTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger embedding generation for a repository",
)
async def trigger_repository_embedding(
    repository_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    v_stmt = (
        select(RepositoryVersion)
        .where(RepositoryVersion.repository_id == repository_id)
        .order_by(RepositoryVersion.created_at.desc())
    )
    res = await db.execute(v_stmt)
    latest_version = res.scalars().first()

    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    background_tasks.add_task(process_version_embeddings, latest_version.id)

    return EmbeddingTriggerResponse(
        repository_id=repository_id,
        version_id=latest_version.id,
        message="Embedding generation enqueued in background",
        status=latest_version.status,
    )