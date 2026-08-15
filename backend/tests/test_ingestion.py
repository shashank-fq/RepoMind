import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.schemas.repository import RepositoryCreate
from app.services.ingestion import extract_repo_name, sync_clone_repo


def test_github_url_validation():
    # Valid URLs
    valid_urls = [
        "https://github.com/psf/requests",
        "https://github.com/fastapi/fastapi.git",
        "https://github.com/owner/repo-name",
    ]
    for url in valid_urls:
        req = RepositoryCreate(github_url=url)
        assert req.github_url is not None

    # Invalid URLs
    invalid_urls = [
        "https://gitlab.com/owner/repo",
        "https://github.com/justowner",
        "http://github.com/psf/requests",  # http instead of https
        "not_a_url",
    ]
    for url in invalid_urls:
        with pytest.raises(ValueError):
            RepositoryCreate(github_url=url)


def test_extract_repo_name():
    assert extract_repo_name("https://github.com/psf/requests") == "psf_requests"
    assert extract_repo_name("https://github.com/fastapi/fastapi.git") == "fastapi_fastapi"


@patch("git.Repo.clone_from")
def test_sync_clone_repo(mock_clone_from, tmp_path):
    mock_repo = MagicMock()
    mock_repo.head.commit.hexsha = "1234567890abcdef1234567890abcdef12345678"
    mock_repo.active_branch.name = "main"
    mock_repo.head.is_detached = False
    mock_clone_from.return_value = mock_repo

    target_dir = tmp_path / "test_repo"
    commit_hash, branch = sync_clone_repo("https://github.com/psf/requests", target_dir)

    assert commit_hash == "1234567890abcdef1234567890abcdef12345678"
    assert branch == "main"
    mock_clone_from.assert_called_once_with(
        url="https://github.com/psf/requests",
        to_path=str(target_dir),
        depth=1,
        single_branch=True,
    )