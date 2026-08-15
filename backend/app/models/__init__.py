# Import all models so Alembic can detect them via Base.metadata
from app.models.user import User
from app.models.repository import Repository, RepositoryVersion
from app.models.code_file import CodeFile
from app.models.code_chunk import CodeChunk
from app.models.conversation import Conversation, Message
from app.models.test_run import TestRun, TestResult
from app.models.evaluation import EvalDatasetItem, EvaluationRun
from app.models.request_log import RequestLog

__all__ = [
    "User",
    "Repository", "RepositoryVersion",
    "CodeFile",
    "CodeChunk",
    "Conversation", "Message",
    "TestRun", "TestResult",
    "EvalDatasetItem", "EvaluationRun",
    "RequestLog",
]