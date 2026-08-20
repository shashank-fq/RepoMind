import asyncio
import logging
import shutil
import uuid
from pathlib import Path
import git
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.schemas.repository import GITHUB_URL_REGEX
from app.services.file_processor import process_version_files
from app.services.chunker import process_version_chunks
from app.services.embeddings import process_version_embeddings

logger = logging.getLogger(__name__)


def extract_repo_name(github_url: str) -> str:
    """Extract owner/repo name from valid GitHub URL."""
    match = GITHUB_URL_REGEX.match(github_url)
    if match:
        repo = match.group("repo").removesuffix(".git")
        owner = match.group("owner")
        return f"{owner}_{repo}"
    return github_url.rstrip("/").split("/")[-1].removesuffix(".git")


def sync_clone_repo(github_url: str, target_dir: Path) -> tuple[str, str]:
    """
    Synchronous helper function to run git clone (runs in thread pool).
    Performs a shallow clone (--depth 1) for speed and disk efficiency.
    Returns (commit_hash, branch_name).
    """
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)

    target_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Cloning {github_url} into {target_dir}...")
    
    # Clone with depth=1 for optimal performance
    repo = git.Repo.clone_from(
        url=github_url,
        to_path=str(target_dir),
        depth=1,
        single_branch=True,
    )

    commit_hash = repo.head.commit.hexsha
    active_branch = repo.active_branch.name if not repo.head.is_detached else "HEAD"
    
    logger.info(f"Successfully cloned {github_url} at commit {commit_hash[:7]}")
    return commit_hash, active_branch


async def process_repository_ingestion(repository_id: uuid.UUID, version_id: uuid.UUID):
    """
    Background worker task executed by FastAPI BackgroundTasks.
    Handles cloning (Phase 3) followed by file processing (Phase 4).
    """
    async with AsyncSessionLocal() as session:
        res_v = await session.execute(select(RepositoryVersion).where(RepositoryVersion.id == version_id))
        version = res_v.scalars().first()
        res_r = await session.execute(select(Repository).where(Repository.id == repository_id))
        repo_obj = res_r.scalars().first()

        if not version or not repo_obj:
            return

        version.status = "cloning"
        await session.commit()

        dest_dir = settings.REPO_STORAGE_DIR / str(repository_id) / str(version_id)

        try:
            commit_hash, _ = await asyncio.wait_for(
                asyncio.to_thread(sync_clone_repo, repo_obj.github_url, dest_dir),
                timeout=float(settings.GIT_CLONE_TIMEOUT_SECONDS)
            )
            version.commit_hash = commit_hash
            version.cloned_path = str(dest_dir)
            version.status = "cloned"
            await session.commit()
        except Exception as e:
            logger.exception(f"Clone failed for {repo_obj.github_url}: {e}")
            version.status = "error"
            await session.commit()
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            return

    # Step 2: File Filtering & Reading (Phase 4)
    logger.info(f"Phase 4: Scanning files for version {version_id}...")
    file_count = await process_version_files(version_id)
    if file_count == 0:
        logger.warning(f"No code files found for version {version_id}.")
        return

    # Step 3: AST & Line Chunking (Phase 5)
    logger.info(f"Phase 5: Chunking code for version {version_id}...")
    chunk_count = await process_version_chunks(version_id)
    if chunk_count == 0:
        logger.warning(f"No chunks produced for version {version_id}.")
        return

    logger.info(f"Phase 6: Generating embeddings for version {version_id}...")
    embedded_count = await process_version_embeddings(version_id)
    logger.info(f"Pipeline complete! Version {version_id} is READY with {embedded_count} vector-embedded chunks.")