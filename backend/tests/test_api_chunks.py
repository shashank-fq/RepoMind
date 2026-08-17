import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk

@pytest.mark.asyncio
async def test_chunks_api_flow():
    async with AsyncSessionLocal() as session:
        repo = Repository(github_url="https://github.com/test/chunkrepo", name="chunkrepo")
        session.add(repo)
        await session.flush()

        version = RepositoryVersion(
            repository_id=repo.id,
            commit_hash="d987654",
            status="chunks_processed",
        )
        session.add(version)
        await session.flush()

        code_file = CodeFile(
            version_id=version.id,
            path="services/auth.py",
            language="python",
            content="class Auth:\n    def login(self): pass",
        )
        session.add(code_file)
        await session.flush()

        chunk1 = CodeChunk(
            file_id=code_file.id,
            start_line=1,
            end_line=2,
            symbol="Auth.login",
            language="python",
            content="def login(self): pass",
        )
        session.add(chunk1)
        await session.commit()

        repo_id = repo.id
        chunk_id = chunk1.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test List Chunks API
        res = await client.get(f"/repositories/{repo_id}/chunks?symbol=login")
        assert res.status_code == 200
        data = res.json()
        assert data["total_chunks"] == 1
        assert data["chunks"][0]["symbol"] == "Auth.login"
        assert data["chunks"][0]["has_embedding"] is False

        # Test Get Single Chunk API
        res_single = await client.get(f"/chunks/{chunk_id}")
        assert res_single.status_code == 200
        data_single = res_single.json()
        assert data_single["symbol"] == "Auth.login"