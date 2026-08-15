"""
Seed a minimal Repository record for manual testing.
Run with:  python -m scripts.seed   (from the backend/ directory)
"""
import asyncio
import uuid

from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion


async def seed():
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=uuid.uuid4(),
            github_url="https://github.com/psf/requests",
            name="requests",
        )
        session.add(repo)
        await session.flush()

        version = RepositoryVersion(
            id=uuid.uuid4(),
            repository_id=repo.id,
            commit_hash="abc123",
            status="ready",
        )
        session.add(version)
        await session.commit()

        print(f"Seeded: Repository {repo.id}, Version {version.id}")


if __name__ == "__main__":
    asyncio.run(seed())
