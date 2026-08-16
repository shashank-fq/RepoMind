from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.schemas.file import (
    CodeFileSummaryResponse,
    CodeFileDetailResponse,
    CodeFilePaginatedResponse,
)

router = APIRouter(tags=["Code Files"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get(
    "/repositories/{repository_id}/files",
    response_model=CodeFilePaginatedResponse,
    summary="List code files in a repository version",
)
async def list_repository_files(
    repository_id: UUID,
    language: str | None = Query(None, description="Filter by language (e.g. python, typescript)"),
    search_path: str | None = Query(None, description="Filter by relative path substring"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    # Get latest version for repo
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

    # Base query for files
    query = select(CodeFile).where(CodeFile.version_id == latest_version.id)

    if language:
        query = query.where(CodeFile.language == language.lower())
    if search_path:
        query = query.where(CodeFile.path.ilike(f"%{search_path}%"))

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total_files = total_res.scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(CodeFile.path).offset(offset).limit(page_size)
    files_res = await db.execute(query)
    files = files_res.scalars().all()

    return CodeFilePaginatedResponse(
        total_files=total_files,
        page=page,
        page_size=page_size,
        files=[CodeFileSummaryResponse.model_validate(f) for f in files],
    )

@router.get(
    "/files/{file_id}",
    response_model=CodeFileDetailResponse,
    summary="Get single code file content",
)
async def get_code_file(file_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(CodeFile).where(CodeFile.id == file_id)
    res = await db.execute(stmt)
    code_file = res.scalars().first()

    if not code_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Code file {file_id} not found",
        )

    return CodeFileDetailResponse.model_validate(code_file)