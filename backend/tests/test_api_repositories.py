import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_create_repository_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch("app.services.ingestion.process_repository_ingestion") as mock_ingest:
            response = await ac.post(
                "/repositories",
                json={"github_url": "https://github.com/psf/requests"}
            )
            assert response.status_code == 202
            data = response.json()
            assert data["github_url"] == "https://github.com/psf/requests"
            assert data["name"] == "psf_requests"
            assert data["latest_version"]["status"] == "pending"


@pytest.mark.asyncio
async def test_get_repository_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Ingest
        with patch("app.services.ingestion.process_repository_ingestion"):
            post_res = await ac.post(
                "/repositories",
                json={"github_url": "https://github.com/pallets/flask"}
            )
            repo_id = post_res.json()["id"]

        # 2. Query status
        status_res = await ac.get(f"/repositories/{repo_id}/status")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "pending"