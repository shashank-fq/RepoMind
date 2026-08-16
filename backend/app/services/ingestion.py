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
        result = await session.execute(
            select(RepositoryVersion).where(RepositoryVersion.id == version_id)
        )
        version = result.scalars().first()
        
        result_repo = await session.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repo_obj = result_repo.scalars().first()

        if not version or not repo_obj:
            logger.error(f"Ingestion failed: Repository/Version record not found ({version_id})")
            return

        version.status = "cloning"
        await session.commit()

        dest_dir = settings.REPO_STORAGE_DIR / str(repository_id) / str(version_id)

        try:
            # Step 1: Clone Repository (Phase 3)
            commit_hash, _ = await asyncio.wait_for(
                asyncio.to_thread(sync_clone_repo, repo_obj.github_url, dest_dir),
                timeout=float(settings.GIT_CLONE_TIMEOUT_SECONDS)
            )

            version.commit_hash = commit_hash
            version.cloned_path = str(dest_dir)
            version.status = "cloned"
            await session.commit()
            
            logger.info(f"Phase 3 cloning complete for version {version_id}")

        except Exception as e:
            logger.exception(f"Error cloning repository {repo_obj.github_url}: {e}")
            version.status = "error"
            await session.commit()
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            return

    # Step 2: File Filtering & Reading (Phase 4)
    logger.info(f"Starting Phase 4 file processing for version {version_id}...")
    file_count = await process_version_files(version_id)
    logger.info(f"Phase 4 complete. Ingested {file_count} code files for version {version_id}.")