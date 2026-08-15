from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    DATABASE_URL: str
    REPO_STORAGE_DIR: Path = BASE_DIR / "storage" / "repos"
    GIT_CLONE_TIMEOUT_SECONDS: int = 300  # 5 minute timeout for cloning
    MAX_REPO_SIZE_MB: int = 500           # soft limit check post-clone

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()