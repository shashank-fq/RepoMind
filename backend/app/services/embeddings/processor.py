import asyncio
import logging
import uuid
from sqlalchemy import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.repository import RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.services.embeddings.factory import get_embedding_provider

logger = logging.getLogger(__name__)

async def process_version_embeddings(
    version_id: uuid.UUID,
    batch_size: int | None = None,
) -> int:
    """
    Generates and stores vector embeddings for all code chunks of a repository version.
    1. Fetches code chunks where embedding is NULL.
    2. Batches text content to prevent OOM.
    3. Offloads model execution to thread pool via asyncio.to_thread.
    4. Updates database records and sets RepositoryVersion.status to 'ready'.
    Returns count of embedded chunks.
    """
    effective_batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
    provider = get_embedding_provider()

    async with AsyncSessionLocal() as session:
        # 1. Fetch RepositoryVersion
        res_v = await session.execute(
            select(RepositoryVersion).where(RepositoryVersion.id == version_id)
        )
        version = res_v.scalars().first()

        if not version:
            logger.error(f"RepositoryVersion {version_id} not found for embedding generation.")
            return 0

        # Update status to embedding
        version.status = "embedding"
        await session.commit()

        try:
            # 2. Get file IDs for version
            res_files = await session.execute(
                select(CodeFile.id).where(CodeFile.version_id == version_id)
            )
            file_ids = res_files.scalars().all()

            if not file_ids:
                logger.warning(f"No code files found for version {version_id}.")
                version.status = "ready"
                await session.commit()
                return 0

            # 3. Query code chunks needing embeddings
            chunks_stmt = (
                select(CodeChunk)
                .where(CodeChunk.file_id.in_(file_ids))
                .where(CodeChunk.embedding.is_(None))
                .order_by(CodeChunk.created_at)
            )
            res_chunks = await session.execute(chunks_stmt)
            chunks_to_embed = res_chunks.scalars().all()

            if not chunks_to_embed:
                logger.info(f"All chunks already have embeddings for version {version_id}.")
                version.status = "ready"
                await session.commit()
                return 0

            logger.info(
                f"Generating embeddings for {len(chunks_to_embed)} chunks (batch size: {effective_batch_size})..."
            )

            embedded_count = 0

            # 4. Process in batches
            for i in range(0, len(chunks_to_embed), effective_batch_size):
                batch_chunks = chunks_to_embed[i : i + effective_batch_size]
                texts = [c.content for c in batch_chunks]

                # Offload synchronous ML model encoding to thread pool
                vectors = await asyncio.to_thread(provider.embed_texts, texts)

                # Assign vectors back to SQLAlchemy objects
                for chunk, vector in zip(batch_chunks, vectors):
                    chunk.embedding = vector

                embedded_count += len(batch_chunks)
                await session.commit()

                logger.info(
                    f"Embedded batch {i // effective_batch_size + 1} ({embedded_count}/{len(chunks_to_embed)} chunks)"
                )

            # 5. Pipeline completion: Mark version as 'ready'!
            version.status = "ready"
            await session.commit()

            logger.info(f"Phase 6 complete. Version {version_id} is now 'ready' for RAG search!")
            return embedded_count

        except Exception as e:
            logger.exception(f"Failed to generate embeddings for version {version_id}: {e}")
            version.status = "error"
            await session.commit()
            return 0