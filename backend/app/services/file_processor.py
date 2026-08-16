import os
from typing import Sequence

from app.config import settings
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

def get_file_language(file_path: Path) -> str | None:
    """
    Determine programming language based on file extension or filename.
    Returns None if the extension is not in the allowed list.
    """
    filename_lower = file_path.name.lower()
    
    # Special exact filename matches
    if filename_lower in ("dockerfile", "containerfile"):
        return "dockerfile"
    if filename_lower == "makefile":
        return "makefile"

    ext = file_path.suffix.lower()
    return settings.EXTENSION_LANGUAGE_MAP.get(ext)

def read_file_content(file_path: Path) -> str | None:
    """
    Safely reads text content of a file using UTF-8 with fallback handling.
    Returns None if reading fails or file is binary.
    """
    if is_binary_file(file_path):
        logger.debug(f"Skipping binary file: {file_path}")
        return None

    try:
        # Attempt UTF-8 read first
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            return content
    except Exception as e:
        logger.warning(f"Could not read text content from {file_path}: {e}")
        return None