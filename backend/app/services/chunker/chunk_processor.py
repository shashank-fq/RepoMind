import logging
import uuid
from sqlalchemy import select, delete
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.repository import RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.services.chunker.base import RawChunkData
from app.services.chunker.python_ast import parse_python_ast_chunks
from app.services.chunker.line_splitter import chunk_by_line_windows

logger = logging.getLogger(__name__)

def chunk_code_file(file_path: str, language: str, content: str) -> list[RawChunkData]:
    """
    Selects chunking strategy based on file extension and language.
    """
    if language.lower() == "python" or file_path.endswith(".py"):
        return parse_python_ast_chunks(content, language=language)
    else:
        return chunk_by_line_windows(content, language=language)

async def process_version_chunks(version_id: uuid.UUID) -> int:
    """
    Processes all code files for a given repository version:
    1. Fetches CodeFile records from database.
    2. Generates CodeChunk entries using AST or line windowing.
    3. Bulk-inserts chunks into code_chunks table.
    4. Updates version status to 'chunks_processed'.
    Returns total chunk count.
    """
    async with AsyncSessionLocal() as session:
        # 1. Fetch RepositoryVersion
        result = await session.execute(
            select(RepositoryVersion).where(RepositoryVersion.id == version_id)
        )
        version = result.scalars().first()

        if not version:
            logger.error(f"Version {version_id} not found for chunk processing.")
            return 0

        # Update status to chunking
        version.status = "chunking"
        await session.commit()

        try:
            # 2. Fetch all CodeFiles for this version
            files_result = await session.execute(
                select(CodeFile).where(CodeFile.version_id == version_id)
            )
            code_files = files_result.scalars().all()

            if not code_files:
                logger.warning(f"No code files found for version {version_id}.")
                version.status = "chunks_processed"
                await session.commit()
                return 0

            # 3. Clear existing chunks for idempotency
            file_ids = [f.id for f in code_files]
            await session.execute(
                delete(CodeChunk).where(CodeChunk.file_id.in_(file_ids))
            )

            # 4. Generate chunks for each file
            db_chunks: list[CodeChunk] = []
            for code_file in code_files:
                raw_chunks = chunk_code_file(
                    file_path=code_file.path,
                    language=code_file.language,
                    content=code_file.content,
                )

                for chunk_data in raw_chunks:
                    db_chunks.append(
                        CodeChunk(
                            file_id=code_file.id,
                            start_line=chunk_data.start_line,
                            end_line=chunk_data.end_line,
                            symbol=chunk_data.symbol,
                            language=chunk_data.language,
                            content=chunk_data.content,
                            embedding=None,  # Populated in Phase 6
                        )
                    )

            # 5. Bulk insert chunks
            session.add_all(db_chunks)

            # Update status to chunks_processed
            version.status = "chunks_processed"
            await session.commit()

            logger.info(
                f"Successfully generated {len(db_chunks)} chunks across {len(code_files)} files for version {version_id}"
            )
            return len(db_chunks)

        except Exception as e:
            logger.exception(f"Failed to process chunks for version {version_id}: {e}")
            version.status = "error"
            await session.commit()
            return 0