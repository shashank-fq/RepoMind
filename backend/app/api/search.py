from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import execute_semantic_search

router = APIRouter(tags=["Semantic Search"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Global or Payload-driven Semantic Vector Search",
    description="Embeds query string and searches matching code chunks across all or targeted repositories."
)
async def global_semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await execute_semantic_search(db, request)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )

@router.post(
    "/repositories/{repository_id}/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Repository-scoped Semantic Vector Search (POST)",
    description="Searches code chunks specifically within the target repository."
)
async def repo_semantic_search_post(
    repository_id: UUID,
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    # Enforce repository_id in request payload
    request.repository_id = repository_id
    try:
        return await execute_semantic_search(db, request)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )

@router.get(
    "/repositories/{repository_id}/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Repository-scoped Semantic Vector Search (GET)",
    description="Convenient GET endpoint for natural language query search via query parameters."
)
async def repo_semantic_search_get(
    repository_id: UUID,
    q: str = Query(..., min_length=1, max_length=2000, description="Natural language search query"),
    top_k: int = Query(10, ge=1, le=100, description="Max results"),
    min_similarity: float = Query(0.0, ge=-1.0, le=1.0, description="Min similarity threshold"),
    language: str | None = Query(None, description="Filter by language"),
    symbol_only: bool = Query(False, description="Filter by symbol presence"),
    db: AsyncSession = Depends(get_db),
):
    request = SearchRequest(
        query=q,
        repository_id=repository_id,
        top_k=top_k,
        min_similarity=min_similarity,
        language=language,
        symbol_only=symbol_only,
    )
    try:
        return await execute_semantic_search(db, request)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )