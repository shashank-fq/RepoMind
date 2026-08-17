import pytest
from app.services.chunker.python_ast import parse_python_ast_chunks
from app.services.chunker.line_splitter import chunk_by_line_windows

PYTHON_SAMPLE = """import os
import sys

class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b

def top_level_function():
    print("Hello World")
"""

INVALID_PYTHON_SAMPLE = """def broken_function(:
    print("Syntax error here"
"""

TYPESCRIPT_SAMPLE = """export class UserService {
    async getUser(id: string) {
        return { id, name: "Alice" };
    }
}
"""

def test_python_ast_symbol_extraction():
    chunks = parse_python_ast_chunks(PYTHON_SAMPLE, language="python")
    symbols = [c.symbol for c in chunks]

    assert "__module__" in symbols
    assert "Calculator.add" in symbols
    assert "Calculator.subtract" in symbols
    assert "top_level_function" in symbols

    # Check line numbers for top_level_function
    top_func_chunk = next(c for c in chunks if c.symbol == "top_level_function")
    assert top_func_chunk.start_line == 10
    assert top_func_chunk.end_line == 11
    assert "def top_level_function():" in top_func_chunk.content

def test_syntax_error_ast_fallback():
    # Should not crash; falls back gracefully to line windows
    chunks = parse_python_ast_chunks(INVALID_PYTHON_SAMPLE, language="python")
    assert len(chunks) > 0
    assert chunks[0].symbol is None

def test_line_windows_fallback():
    chunks = chunk_by_line_windows(TYPESCRIPT_SAMPLE, language="typescript")
    assert len(chunks) > 0
    assert chunks[0].start_line == 1
    assert chunks[0].language == "typescript"