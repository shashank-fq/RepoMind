import uuid
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_create_repository_endpoint():
    unique_url = f"https://github.com/psf/requests-test-{uuid.uuid4().hex[:6]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch("app.services.ingestion.process_repository_ingestion"):
            response = await ac.post(
                "/repositories",
                json={"github_url": unique_url}
            )
            assert response.status_code == 202
            data = response.json()
            assert data["github_url"] == unique_url
            assert data["latest_version"]["status"] == "pending"


@pytest.mark.asyncio
async def test_get_repository_status():
    unique_url = f"https://github.com/pallets/flask-status-{uuid.uuid4().hex[:6]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Ingest
        with patch("app.services.ingestion.process_repository_ingestion"):
            post_res = await ac.post(
                "/repositories",
                json={"github_url": unique_url}
            )
            repo_id = post_res.json()["id"]

        # 2. Query status
        status_res = await ac.get(f"/repositories/{repo_id}/status")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "pending"