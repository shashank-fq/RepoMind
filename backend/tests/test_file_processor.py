import pytest
from pathlib import Path

from app.services.file_processor import (
    is_binary_file,
    get_file_language,
    read_file_content,
    scan_repository_directory,
)


def test_is_binary_file(tmp_path):
    # Text file
    text_file = tmp_path / "sample.py"
    text_file.write_text("print('Hello World')", encoding="utf-8")
    assert is_binary_file(text_file) is False

    # Binary file (contains null byte)
    bin_file = tmp_path / "sample.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04")
    assert is_binary_file(bin_file) is True


def test_get_file_language():
    assert get_file_language(Path("main.py")) == "python"
    assert get_file_language(Path("app.tsx")) == "typescript"
    assert get_file_language(Path("Dockerfile")) == "dockerfile"
    assert get_file_language(Path("styles.css")) == "css"
    assert get_file_language(Path("image.png")) is None
    assert get_file_language(Path("binary.exe")) is None