import os
from typing import Sequence
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import AsyncSessionLocal
from app.models.repository import RepositoryVersion
from app.models.code_file import CodeFile
from app.config import settings
import logging
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class ProcessedFileData:
    relative_path: str
    language: str
    content: str


def is_binary_file(file_path: Path) -> bool:
    """
    Check if a file is binary by inspecting the first 8192 bytes for null characters (0x00).
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
            return False
    except Exception as e:
        logger.warning(f"Failed to check binary status for {file_path}: {e}")
        return True

def get_file_language(file_path: Path) -> str | None:
    """
    Determine programming language based on file extension or filename.
    Returns None if the extension is not in the allowed list.
    """
    filename_lower = file_path.name.lower()
    
    # Special exact filename matches
    if filename_lower in ("dockerfile", "containerfile"):
        return "dockerfile"
    if filename_lower == "makefile":
        return "makefile"

    ext = file_path.suffix.lower()
    return settings.EXTENSION_LANGUAGE_MAP.get(ext)

def read_file_content(file_path: Path) -> str | None:
    """
    Safely reads text content of a file using UTF-8 with fallback handling.
    Returns None if reading fails or file is binary.
    """
    if is_binary_file(file_path):
        logger.debug(f"Skipping binary file: {file_path}")
        return None

    try:
        # Attempt UTF-8 read first
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            return content
    except Exception as e:
        logger.warning(f"Could not read text content from {file_path}: {e}")
        return None

def scan_repository_directory(repo_root: Path) -> list[ProcessedFileData]:
    """
    Traverses the cloned repo directory recursively, skipping ignored directories
    and extracting allowed source files. Returns a list of ProcessedFileData objects.
    """
    processed_files: list[ProcessedFileData] = []

    if not repo_root.exists() or not repo_root.is_dir():
        logger.error(f"Repository root directory does not exist: {repo_root}")
        return processed_files

    for root, dirs, files in os.walk(repo_root, topdown=True):
        # Prune ignored directories in-place so os.walk does not recurse into them
        dirs[:] = [d for d in dirs if d not in settings.IGNORED_DIRS and not d.startswith(".")]

        for file_name in files:
            file_path = Path(root) / file_name

            # Skip hidden files starting with '.' unless specifically mapped
            if file_name.startswith(".") and not file_name.endswith((".dockerfile", ".gitignore", ".env.example")):
                continue

            # Check language mapping
            language = get_file_language(file_path)
            if not language:
                continue

            # Check file size limit
            try:
                file_size = file_path.stat().st_size
                if file_size == 0:
                    logger.debug(f"Skipping empty file: {file_path}")
                    continue
                if file_size > settings.MAX_FILE_SIZE_BYTES:
                    logger.warning(f"Skipping oversized file ({file_size} bytes): {file_path}")
                    continue
            except OSError as e:
                logger.warning(f"Could not stat file {file_path}: {e}")
                continue

            # Read content
            content = read_file_content(file_path)
            if content is None:
                continue

            # Calculate relative path from repository root
            rel_path = file_path.relative_to(repo_root).as_posix()

            processed_files.append(
                ProcessedFileData(
                    relative_path=rel_path,
                    language=language,
                    content=content,
                )
            )

    logger.info(f"Scanned {repo_root}: found {len(processed_files)} processable source files.")
    return processed_files

async def process_version_files(version_id: uuid.UUID) -> int:
    """
    Fetches the RepositoryVersion record, scans the cloned files from disk,
    inserts records into code_files table, and updates version status to 'files_processed'.
    Returns total count of processed code files.
    """
    async with AsyncSessionLocal() as session:
        # 1. Fetch RepositoryVersion
        result = await session.execute(
            select(RepositoryVersion).where(RepositoryVersion.id == version_id)
        )
        version = result.scalars().first()

        if not version:
            logger.error(f"Version {version_id} not found for file processing.")
            return 0

        if not version.cloned_path or not Path(version.cloned_path).exists():
            logger.error(f"Cloned path missing or invalid for version {version_id}: {version.cloned_path}")
            version.status = "error"
            await session.commit()
            return 0

        # 2. Update status to processing_files
        version.status = "processing_files"
        await session.commit()

        repo_root = Path(version.cloned_path)

        try:
            # 3. Scan directory in a thread pool (I/O bound)
            scanned_files = scan_repository_directory(repo_root)

            # 4. Remove any existing code files for this version (idempotency safety)
            await session.execute(
                delete(CodeFile).where(CodeFile.version_id == version_id)
            )

            # 5. Bulk prepare CodeFile instances
            db_code_files = [
                CodeFile(
                    version_id=version_id,
                    path=item.relative_path,
                    language=item.language,
                    content=item.content,
                )
                for item in scanned_files
            ]

            # 6. Bulk add and commit
            session.add_all(db_code_files)
            
            # Update version status to files_processed (ready for Phase 5 chunking)
            version.status = "files_processed"
            await session.commit()

            logger.info(f"Successfully processed {len(db_code_files)} files for version {version_id}")
            return len(db_code_files)

        except Exception as e:
            logger.exception(f"Failed to process files for version {version_id}: {e}")
            version.status = "error"
            await session.commit()
            return 0