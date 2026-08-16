from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    DATABASE_URL: str
    REPO_STORAGE_DIR: Path = BASE_DIR / "storage" / "repos"
    GIT_CLONE_TIMEOUT_SECONDS: int = 300  # 5 minute timeout for cloning
    MAX_REPO_SIZE_MB: int = 500           # soft limit check post-clone

    MAX_FILE_SIZE_BYTES: int = 1_048_576

    IGNORED_DIRS: set[str] = {
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        "target",
        "bin",
        "obj",
        ".idea",
        ".vscode",
        "vendor",
        "coverage",
        ".next",
        ".nuxt",
    }

    EXTENSION_LANGUAGE_MAP: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "scss",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".markdown": "markdown",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".dockerfile": "dockerfile",
        "dockerfile": "dockerfile",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".php": "php",
        ".rb": "ruby",
        ".kt": "kotlin",
        ".swift": "swift",
        ".scala": "scala",
        ".toml": "toml",
        ".xml": "xml",
        ".ini": "ini",
    }
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()