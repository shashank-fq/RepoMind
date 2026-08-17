from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.repository import RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.schemas.chunk import CodeChunkResponse, CodeChunkPaginatedResponse

router = APIRouter(tags=["Code Chunks"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get(
    "/repositories/{repository_id}/chunks",
    response_model=CodeChunkPaginatedResponse,
    summary="List code chunks in a repository",
)
async def list_repository_chunks(
    repository_id: UUID,
    symbol: str | None = Query(None, description="Filter by symbol substring (e.g. login, User)"),
    language: str | None = Query(None, description="Filter by language"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    # Fetch latest version
    version_stmt = (
        select(RepositoryVersion)
        .where(RepositoryVersion.repository_id == repository_id)
        .order_by(RepositoryVersion.created_at.desc())
    )
    v_res = await db.execute(version_stmt)
    latest_version = v_res.scalars().first()

    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No versions found for repository {repository_id}",
        )

    # Subquery for file IDs
    file_ids_query = select(CodeFile.id).where(CodeFile.version_id == latest_version.id)

    # Base query for chunks
    query = select(CodeChunk).where(CodeChunk.file_id.in_(file_ids_query))

    if symbol:
        query = query.where(CodeChunk.symbol.ilike(f"%{symbol}%"))
    if language:
        query = query.where(CodeChunk.language == language.lower())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total_chunks = total_res.scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(CodeChunk.created_at).offset(offset).limit(page_size)
    res = await db.execute(query)
    chunks = res.scalars().all()

    chunk_responses = [
        CodeChunkResponse(
            id=c.id,
            file_id=c.file_id,
            start_line=c.start_line,
            end_line=c.end_line,
            symbol=c.symbol,
            language=c.language,
            content=c.content,
            has_embedding=c.embedding is not None,
            created_at=c.created_at,
        )
        for c in chunks
    ]

    return CodeChunkPaginatedResponse(
        total_chunks=total_chunks,
        page=page,
        page_size=page_size,
        chunks=chunk_responses,
    )

@router.get(
    "/chunks/{chunk_id}",
    response_model=CodeChunkResponse,
    summary="Get single code chunk details",
)
async def get_chunk_detail(chunk_id: UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(CodeChunk).where(CodeChunk.id == chunk_id))
    chunk = res.scalars().first()

    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Code chunk {chunk_id} not found",
        )

    return CodeChunkResponse(
        id=chunk.id,
        file_id=chunk.file_id,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        symbol=chunk.symbol,
        language=chunk.language,
        content=chunk.content,
        has_embedding=chunk.embedding is not None,
        created_at=chunk.created_at,
    )
