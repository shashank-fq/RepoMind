import sys
from pathlib import Path

import pytest

# Add backend/ to sys.path so `app` is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Tell pytest-asyncio to auto-detect async tests
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    yield
    from app.database import engine
    await engine.dispose()

