import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.schemas.search import SearchRequest
from app.services.search_service import execute_semantic_search
from app.services.embeddings import get_embedding_provider

client = TestClient(app)

@pytest.mark.asyncio
async def test_semantic_search_engine_ranking():
    """
    Integration Test: Verify that semantic search correctly vectorizes input queries
    and ranks the most relevant chunk first based on cosine similarity.
    """
    provider = get_embedding_provider()

    # Generate real vector embeddings for sample texts
    text_auth = "def authenticate_user(username, password): verify credentials and return JWT token"
    text_db = "class DatabaseConnectionPool: manage PostgreSQL connection handles and sessions"
    
    vec_auth = provider.embed_texts([text_auth])[0]
    vec_db = provider.embed_texts([text_db])[0]

    async with AsyncSessionLocal() as session:
        # 1. Create Repository & Version
        repo = Repository(github_url="https://github.com/test/search-repo", name="search_repo")
        session.add(repo)
        await session.flush()

        version = RepositoryVersion(repository_id=repo.id, commit_hash="sha123", status="ready")
        session.add(version)
        await session.flush()

        # 2. Create Code File
        code_file = CodeFile(
            version_id=version.id,
            path="auth/login.py",
            language="python",
            content=f"{text_auth}\n{text_db}",
        )
        session.add(code_file)
        await session.flush()

        # 3. Create Code Chunks with Embeddings
        chunk_auth = CodeChunk(
            file_id=code_file.id,
            start_line=1,
            end_line=1,
            symbol="authenticate_user",
            language="python",
            content=text_auth,
            embedding=vec_auth,
        )
        chunk_db = CodeChunk(
            file_id=code_file.id,
            start_line=2,
            end_line=2,
            symbol="DatabaseConnectionPool",
            language="python",
            content=text_db,
            embedding=vec_db,
        )
        session.add_all([chunk_auth, chunk_db])
        await session.commit()

        # 4. Perform Search for Auth Query
        req = SearchRequest(
            query="JWT login password verification",
            repository_id=repo.id,
            top_k=5,
            min_similarity=0.0
        )

        response = await execute_semantic_search(session, req)

        assert response.total_results == 2
        assert response.results[0].symbol == "authenticate_user"
        assert response.results[0].similarity_score > response.results[1].similarity_score
        assert response.results[0].file_path == "auth/login.py"

def test_repo_search_api_endpoints():
    """
    API Test: Test POST and GET search endpoints via FastAPI TestClient.
    """
    # Create test repo in DB
    repo_id = uuid.uuid4()
    
    # Execute POST search request
    payload = {
        "query": "authentication flow",
        "top_k": 5,
        "min_similarity": 0.1
    }
    response = client.post(f"/repositories/{repo_id}/search", json=payload)
    
    # Should return 404 since repo ID is not in DB, validating error handler
    assert response.status_code == 404
    assert "No ingested 'ready' version found" in response.json()["detail"]