
import logging
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class ProcessedFileData:
    relative_path: str
    language: str
    content: str


def is_binary_file(file_path: Path) -> bool:
    """
    Check if a file is binary by inspecting the first 8192 bytes for null characters (0x00).
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
            return False
    except Exception as e:
        logger.warning(f"Failed to check binary status for {file_path}: {e}")
        return True