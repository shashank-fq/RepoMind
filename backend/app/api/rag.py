from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.repository import Repository
from app.schemas.rag import RAGQueryRequest, RAGResponse
from app.services.rag_service import generate_rag_answer

router = APIRouter(tags=["RAG & Answers"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post(
    "/repositories/{repository_id}/ask",
    response_model=RAGResponse,
    summary="Ask a natural language question about the repository code",
)
async def ask_repository_question(
    repository_id: UUID,
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Grounded RAG Endpoint:
    1. Retrieves relevant code chunks for the question via vector similarity search.
    2. Constructs prompt context with strict citation rules.
    3. Queries LLM and parses explicit [file_path:start-end] citations.
    4. Returns grounded answer with verifiable source citations.
    """
    res = await db.execute(select(Repository).where(Repository.id == repository_id))
    repo = res.scalars().first()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    try:
        response = await generate_rag_answer(repository_id, request, db)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG question generation failed: {str(e)}",
        )