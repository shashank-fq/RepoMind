"""
Verify that we can insert and query a repository + code chunk round-trip.
"""
import asyncio
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk


@pytest.mark.asyncio
async def test_repository_chunk_roundtrip():
    async with AsyncSessionLocal() as session:
        # 1. Create repo
        repo = Repository(github_url="https://github.com/test/test", name="test")
        session.add(repo)
        await session.flush()

        # 2. Create version
        version = RepositoryVersion(
            repository_id=repo.id, commit_hash="aaa000", status="ready"
        )
        session.add(version)
        await session.flush()

        # 3. Create file
        file = CodeFile(
            version_id=version.id,
            path="auth/service.py",
            language="python",
            content="def login(): pass",
        )
        session.add(file)
        await session.flush()

        # 4. Create chunk (no embedding yet)
        chunk = CodeChunk(
            file_id=file.id,
            start_line=1,
            end_line=1,
            symbol="login",
            language="python",
            content="def login(): pass",
        )
        session.add(chunk)
        await session.commit()

        # 5. Query it back
        from sqlalchemy import select
        result = await session.execute(
            select(CodeChunk).where(CodeChunk.symbol == "login")
        )
        fetched = result.scalars().first()

        assert fetched is not None
        assert fetched.content == "def login(): pass"
        assert fetched.start_line == 1