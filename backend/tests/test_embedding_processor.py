import pytest
import uuid
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.services.embeddings import process_version_embeddings

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

    # 2. Run embedding processor
    embedded_count = await process_version_embeddings(version_id)
    assert embedded_count == 1

    # 3. Verify vector saved in DB and status is 'ready'
    async with AsyncSessionLocal() as session:
        v_res = await session.execute(select(RepositoryVersion).where(RepositoryVersion.id == version_id))
        updated_version = v_res.scalars().first()
        assert updated_version.status == "ready"

        c_res = await session.execute(select(CodeChunk).where(CodeChunk.file_id == code_file.id))
        updated_chunk = c_res.scalars().first()
        assert updated_chunk.embedding is not None
        assert len(updated_chunk.embedding) == 384
    