import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile


@pytest.mark.asyncio
async def test_file_api_flow():
    # 1. Seed DB with test repo, version, and code file
    async with AsyncSessionLocal() as session:
        repo = Repository(github_url="https://github.com/test/filerepo", name="filerepo")
        session.add(repo)
        await session.flush()

        version = RepositoryVersion(
            repository_id=repo.id,
            commit_hash="c123456",
            status="files_processed",
        )
        session.add(version)
        await session.flush()

        file1 = CodeFile(
            version_id=version.id,
            path="backend/main.py",
            language="python",
            content="from fastapi import FastAPI\napp = FastAPI()",
        )
        file2 = CodeFile(
            version_id=version.id,
            path="frontend/src/App.tsx",
            language="typescript",
            content="export const App = () => <div>Hello</div>;",
        )
        session.add_all([file1, file2])
        await session.commit()

        repo_id = repo.id
        file1_id = file1.id

    # 2. Test GET /repositories/{repository_id}/files
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        list_res = await ac.get(f"/repositories/{repo_id}/files")
        assert list_res.status_code == 200
        data = list_res.json()
        assert data["total_files"] == 2
        assert len(data["files"]) == 2

        # Filter by language
        lang_res = await ac.get(f"/repositories/{repo_id}/files?language=python")
        assert lang_res.status_code == 200
        lang_data = lang_res.json()
        assert lang_data["total_files"] == 1
        assert lang_data["files"][0]["path"] == "backend/main.py"

        # 3. Test GET /files/{file_id}
        detail_res = await ac.get(f"/files/{file1_id}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["path"] == "backend/main.py"
        assert "FastAPI" in detail_data["content"]