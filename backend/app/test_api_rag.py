import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_ask_endpoint_repo_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        fake_id = "00000000-0000-0000-0000-000000000000"
        res = await ac.post(
            f"/repositories/{fake_id}/ask",
            json={"question": "How does authentication work?"}
        )
        assert res.status_code == 404