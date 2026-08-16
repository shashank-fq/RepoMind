from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
    RepositoryVersionResponse,
    IngestionStatusResponse,
)
from app.services.ingestion import extract_repo_name, process_repository_ingestion

router = APIRouter(prefix="/repositories", tags=["Repositories"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a new GitHub repository",
)
async def create_repository(
    payload: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a public GitHub URL, creates repository records, 
    and triggers background cloning process.
    """
    # 1. Check if repository already exists
    stmt = select(Repository).where(Repository.github_url == payload.github_url)
    res = await db.execute(stmt)
    existing_repo = res.scalars().first()

    repo_name = extract_repo_name(payload.github_url)

    if existing_repo:
        repo = existing_repo
    else:
        repo = Repository(
            github_url=payload.github_url,
            name=repo_name,
        )
        db.add(repo)
        await db.flush()

    # 2. Create new version record in pending state
    version = RepositoryVersion(
        repository_id=repo.id,
        commit_hash="pending",  # Will be updated after clone
        status="pending",
    )
    db.add(version)
    await db.commit()
    await db.refresh(repo)
    await db.refresh(version)

    # 3. Enqueue asynchronous cloning in background task
    background_tasks.add_task(
        process_repository_ingestion,
        repository_id=repo.id,
        version_id=version.id,
    )

    return RepositoryResponse(
        id=repo.id,
        github_url=repo.github_url,
        name=repo.name,
        created_at=repo.created_at,
        latest_version=RepositoryVersionResponse.model_validate(version),
    )


@router.get(
    "",
    response_model=list[RepositoryResponse],
    summary="List all ingested repositories",
)
async def list_repositories(db: AsyncSession = Depends(get_db)):
    stmt = select(Repository).options(selectinload(Repository.versions))
    res = await db.execute(stmt)
    repos = res.scalars().all()
    
    response = []
    for r in repos:
        latest = sorted(r.versions, key=lambda v: (v.created_at, str(v.id)), reverse=True)[0] if r.versions else None
        response.append(
            RepositoryResponse(
                id=r.id,
                github_url=r.github_url,
                name=r.name,
                created_at=r.created_at,
                latest_version=RepositoryVersionResponse.model_validate(latest) if latest else None,
            )
        )
    return response


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
    summary="Get repository details by ID",
)
async def get_repository(repository_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Repository)
        .where(Repository.id == repository_id)
        .options(selectinload(Repository.versions))
    )
    res = await db.execute(stmt)
    repo = res.scalars().first()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    latest = sorted(repo.versions, key=lambda v: (v.created_at, str(v.id)), reverse=True)[0] if repo.versions else None
    return RepositoryResponse(
        id=repo.id,
        github_url=repo.github_url,
        name=repo.name,
        created_at=repo.created_at,
        latest_version=RepositoryVersionResponse.model_validate(latest) if latest else None,
    )


@router.get(
    "/{repository_id}/status",
    response_model=IngestionStatusResponse,
    summary="Check ingestion status of repository",
)
async def get_ingestion_status(repository_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Repository)
        .where(Repository.id == repository_id)
        .options(selectinload(Repository.versions))
    )
    res = await db.execute(stmt)
    repo = res.scalars().first()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    if not repo.versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No version records found for repository",
        )

    latest_version = sorted(repo.versions, key=lambda v: (v.created_at, str(v.id)), reverse=True)[0]


    return IngestionStatusResponse(
        repository_id=repo.id,
        version_id=latest_version.id,
        name=repo.name,
        status=latest_version.status,
        commit_hash=latest_version.commit_hash if latest_version.commit_hash != "pending" else None,
    )