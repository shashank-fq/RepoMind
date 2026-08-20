import pytest

from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk

@pytest.mark.asyncio
async def test_process_version_embeddings():
    async with AsyncSessionLocal() as session:
        # 1. Create DB records
        repo = Repository(github_url="https://github.com/test/embed-test", name="embed_test")
        session.add(repo)
        await session.flush()

        version = RepositoryVersion(repository_id=repo.id, commit_hash="abc", status="chunks_processed")
        session.add(version)
        await session.flush()

        code_file = CodeFile(
            version_id=version.id,
            path="auth/login.py",
            language="python",
            content="def authenticate(user, pwd): pass",
        )
        session.add(code_file)
        await session.flush()

        chunk = CodeChunk(
            file_id=code_file.id,
            start_line=1,
            end_line=1,
            symbol="authenticate",
            language="python",
            content="def authenticate(user, pwd): pass",
            embedding=None,
        )
        session.add(chunk)
        await session.commit()
        version_id = version.id

    