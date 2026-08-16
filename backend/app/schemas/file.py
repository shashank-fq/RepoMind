from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CodeFileSummaryResponse(BaseModel):
    id: UUID
    version_id: UUID
    path: str
    language: str
    created_at: datetime

    class Config:
        from_attributes = True


class CodeFileDetailResponse(CodeFileSummaryResponse):
    content: str

    class Config:
        from_attributes = True


class CodeFilePaginatedResponse(BaseModel):
    total_files: int
    page: int
    page_size: int
    files: list[CodeFileSummaryResponse]