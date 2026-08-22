import logging
import time
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.repository import RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.schemas.search import SearchRequest, SearchResultItem, SearchResponse
from app.services.embeddings import get_embedding_provider

logger = logging.getLogger(__name__)

async def get_latest_ready_version(
    db: AsyncSession,
    repository_id: uuid.UUID
) -> RepositoryVersion | None:
    """
    Helper function to resolve the latest 'ready' RepositoryVersion for a repository.
    """
    stmt = (
        select(RepositoryVersion)
        .where(RepositoryVersion.repository_id == repository_id)
        .where(RepositoryVersion.status == "ready")
        .order_by(RepositoryVersion.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().first()

async def execute_semantic_search(
    db: AsyncSession,
    request: SearchRequest,
) -> SearchResponse:
    """
    Executes semantic vector search across code chunks using pgvector:
    1. Resolves target RepositoryVersion ID (or uses provided version_id).
    2. Vectorizes the natural language input query using the active EmbeddingProvider.
    3. Executes pgvector cosine distance query (<=>) with filtering and threshold constraints.
    4. Computes similarity score = 1.0 - cosine_distance.
    5. Returns ranked SearchResponse with execution metrics.
    """
    start_time = time.perf_counter()

    # 1. Resolve version_id
    target_version_id = request.version_id
    target_repo_id = request.repository_id

    if not target_version_id and target_repo_id:
        version = await get_latest_ready_version(db, target_repo_id)
        if not version:
            raise ValueError(f"No ingested 'ready' version found for repository ID {target_repo_id}")
        target_version_id = version.id
    elif target_version_id and not target_repo_id:
        res_v = await db.execute(select(RepositoryVersion).where(RepositoryVersion.id == target_version_id))
        v_obj = res_v.scalars().first()
        if v_obj:
            target_repo_id = v_obj.repository_id

    # 2. Embed the query text
    provider = get_embedding_provider()
    query_vectors = provider.embed_texts([request.query])
    if not query_vectors or not query_vectors[0]:
        raise RuntimeError("Failed to generate vector embedding for search query.")
    
    query_vector = query_vectors[0]

    # 3. Construct SQLAlchemy pgvector Distance & Similarity Expressions
    # pgvector provides .cosine_distance() method on Vector columns
    distance_expr = CodeChunk.embedding.cosine_distance(query_vector).label("distance")
    similarity_expr = (1.0 - distance_expr).label("similarity_score")

    # Build core query joining CodeChunk -> CodeFile -> RepositoryVersion
    stmt = (
        select(
            CodeChunk,
            CodeFile.path.label("file_path"),
            distance_expr,
            similarity_expr,
        )
        .join(CodeFile, CodeChunk.file_id == CodeFile.id)
        .join(RepositoryVersion, CodeFile.version_id == RepositoryVersion.id)
        .where(CodeChunk.embedding.is_not(None))
    )

    # Apply Repository / Version Filters
    if target_version_id:
        stmt = stmt.where(RepositoryVersion.id == target_version_id)
    elif target_repo_id:
        stmt = stmt.where(RepositoryVersion.repository_id == target_repo_id)

    # Apply Metadata Filters
    if request.language:
        stmt = stmt.where(CodeChunk.language == request.language.lower())

    if request.symbol_only:
        stmt = stmt.where(CodeChunk.symbol.is_not(None))

    # Apply Minimum Similarity Threshold Filter
    if request.min_similarity > -1.0:
        stmt = stmt.where(similarity_expr >= request.min_similarity)

    # Apply Vector Nearest-Neighbor Ordering & Pagination Top_K Limit
    top_k_limit = min(request.top_k or settings.DEFAULT_SEARCH_TOP_K, settings.MAX_SEARCH_TOP_K)
    stmt = stmt.order_by(distance_expr.asc()).limit(top_k_limit)

    # Execute DB query
    result = await db.execute(stmt)
    rows = result.all()

    # 4. Format Search Results
    search_items: list[SearchResultItem] = []
    for row in rows:
        chunk: CodeChunk = row.CodeChunk
        file_path: str = row.file_path
        distance_val: float = float(row.distance)
        similarity_val: float = float(row.similarity_score)

        search_items.append(
            SearchResultItem(
                chunk_id=chunk.id,
                file_id=chunk.file_id,
                file_path=file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                symbol=chunk.symbol,
                language=chunk.language,
                content=chunk.content,
                similarity_score=round(similarity_val, 4),
                distance=round(distance_val, 4),
            )
        )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return SearchResponse(
        query=request.query,
        repository_id=target_repo_id,
        version_id=target_version_id,
        total_results=len(search_items),
        results=search_items,
        execution_time_ms=elapsed_ms,
        provider=provider.__class__.__name__,
    )

# Alias for compatibility across service modules
search_repository_code = execute_semantic_search