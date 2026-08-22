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

    TARGET_CHUNK_LINES: int = 50          # Target lines for fallback splitter
    CHUNK_OVERLAP_LINES: int = 10         # Overlap lines for fallback windowing
    MAX_CHUNK_LINES: int = 150            # Sub-split oversized AST blocks above this
    MIN_CHUNK_LINES: int = 3              # Ignore tiny noise chunks (< 3 lines)

    EMBEDDING_PROVIDER: str = "local"  # "local" | "openai"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"  # local default (dim=384)
    EMBEDDING_BATCH_SIZE: int = 64
    OPENAI_API_KEY: str | None = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    DEFAULT_SEARCH_TOP_K: int = 10
    MAX_SEARCH_TOP_K: int = 100
    DEFAULT_MIN_SIMILARITY: float = 0.0  # Range: -1.0 to 1.0 (0.0 filters negative correlations)
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()