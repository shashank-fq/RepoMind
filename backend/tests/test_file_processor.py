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


def test_scan_repository_directory(tmp_path):
    # Setup mock repo directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules" / "express").mkdir(parents=True)
    (tmp_path / ".git").mkdir()

    # Valid source files
    py_file = tmp_path / "src" / "app.py"
    py_file.write_text("def main(): pass", encoding="utf-8")

    ts_file = tmp_path / "src" / "index.ts"
    ts_file.write_text("console.log('hi');", encoding="utf-8")

    # Ignored files
    nm_file = tmp_path / "node_modules" / "express" / "index.js"
    nm_file.write_text("module.exports = {};", encoding="utf-8")

    git_file = tmp_path / ".git" / "config"
    git_file.write_text("[core]", encoding="utf-8")

    ignored_ext_file = tmp_path / "src" / "logo.png"
    ignored_ext_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00")

    # Scan directory
    scanned = scan_repository_directory(tmp_path)

    paths = [item.relative_path for item in scanned]
    assert "src/app.py" in paths
    assert "src/index.ts" in paths
    assert "node_modules/express/index.js" not in paths
    assert ".git/config" not in paths
    assert "src/logo.png" not in paths

    assert len(scanned) == 2