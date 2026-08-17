import ast
import logging
from app.config import settings
from app.services.chunker.base import RawChunkData
from app.services.chunker.line_splitter import chunk_by_line_windows

logger = logging.getLogger(__name__)

def parse_python_ast_chunks(code: str, language: str = "python") -> list[RawChunkData]:
    """
    Parses Python code into semantic AST chunks (classes, functions, async functions, module imports).
    Falls back to line windowing if AST parsing encounters a SyntaxError or IndentationError.
    """
    try:
        tree = ast.parse(code)
    except (SyntaxError, IndentationError, ValueError, Exception) as e:
        logger.warning(f"AST parsing failed (falling back to line splitter): {e}")
        return chunk_by_line_windows(code, language=language)

    lines = code.splitlines(keepends=True)
    total_lines = len(lines)
    if total_lines == 0:
        return []

    chunks: list[RawChunkData] = []
    visited_line_ranges: list[tuple[int, int]] = []

    # 1. Extract Module Level Header / Imports (lines before first definition)
    first_def_line = total_lines + 1
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first_def_line = min(first_def_line, getattr(node, "lineno", total_lines + 1))

    if first_def_line > 1 and first_def_line <= total_lines:
        header_content = "".join(lines[: first_def_line - 1]).strip()
        header_lines = first_def_line - 1
        if header_content and (header_lines >= settings.MIN_CHUNK_LINES or total_lines < settings.MIN_CHUNK_LINES):
            chunks.append(
                RawChunkData(
                    start_line=1,
                    end_line=first_def_line - 1,
                    symbol="__module__",
                    content=header_content,
                    language=language,
                )
            )
            visited_line_ranges.append((1, first_def_line - 1))

    # 2. Extract AST Class and Function Nodes
    def process_node(node: ast.AST, prefix: str = ""):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start_line = getattr(node, "lineno", None)
            end_line = getattr(node, "end_lineno", None)

            if not start_line or not end_line:
                return

            current_symbol = f"{prefix}.{node.name}" if prefix else node.name
            chunk_line_count = end_line - start_line + 1

            # If node is oversized, sub-chunk it with symbol attribution
            if chunk_line_count > settings.MAX_CHUNK_LINES:
                node_code = "".join(lines[start_line - 1 : end_line])
                sub_chunks = chunk_by_line_windows(
                    node_code,
                    language=language,
                    symbol_override=current_symbol,
                    line_offset=start_line - 1,
                )
                chunks.extend(sub_chunks)
            elif chunk_line_count >= settings.MIN_CHUNK_LINES or total_lines < settings.MIN_CHUNK_LINES:
                node_content = "".join(lines[start_line - 1 : end_line]).strip()
                if node_content:
                    chunks.append(
                        RawChunkData(
                            start_line=start_line,
                            end_line=end_line,
                            symbol=current_symbol,
                            content=node_content,
                            language=language,
                        )
                    )
            
            visited_line_ranges.append((start_line, end_line))

            # Recurse into Class methods
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        process_node(child, prefix=current_symbol)

    for node in tree.body:
        process_node(node)

    if not chunks:
        return chunk_by_line_windows(code, language=language)

    chunks.sort(key=lambda c: c.start_line)
    return chunks