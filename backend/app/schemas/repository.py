import re
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, HttpUrl, field_validator


GITHUB_URL_REGEX = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)(?:\.git)?$"
)


class RepositoryCreate(BaseModel):
    github_url: str

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        match = GITHUB_URL_REGEX.match(v)
        if not match:
            raise ValueError(
                "Invalid GitHub URL format. Must be like: https://github.com/owner/repository"
            )
        return v


class RepositoryVersionResponse(BaseModel):
    id: UUID
    repository_id: UUID
    commit_hash: str
    status: str
    cloned_path: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class RepositoryResponse(BaseModel):
    id: UUID
    github_url: str
    name: str
    created_at: datetime
    latest_version: RepositoryVersionResponse | None = None

    class Config:
        from_attributes = True


class IngestionStatusResponse(BaseModel):
    repository_id: UUID
    version_id: UUID
    name: str
    status: str  # pending | cloning | cloned | processing | ready | error
    commit_hash: str | None = None
    error_message: str | None = None
