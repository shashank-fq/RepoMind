from app.config import settings
from app.services.chunker.base import RawChunkData

def chunk_by_line_windows(
    code: str,
    language: str,
    symbol_override: str | None = None,
    line_offset: int = 0,
) -> list[RawChunkData]:
    """
    Splits text or code files into sliding line windows (e.g. 50 lines with 10-line overlap).
    Computes exact 1-based start_line and end_line bounds.
    """
    lines = code.splitlines(keepends=True)
    total_lines = len(lines)

    if total_lines == 0:
        return []

    target_lines = settings.TARGET_CHUNK_LINES
    overlap = settings.CHUNK_OVERLAP_LINES
    step = max(1, target_lines - overlap)

    chunks: list[RawChunkData] = []
    start_idx = 0

    while start_idx < total_lines:
        end_idx = min(start_idx + target_lines, total_lines)
        
        # Extract line slice
        chunk_lines = lines[start_idx:end_idx]
        chunk_content = "".join(chunk_lines).strip()

        actual_start_line = line_offset + start_idx + 1
        actual_end_line = line_offset + end_idx

        if chunk_content and (end_idx - start_idx) >= settings.MIN_CHUNK_LINES:
            chunks.append(
                RawChunkData(
                    start_line=actual_start_line,
                    end_line=actual_end_line,
                    symbol=symbol_override,
                    content=chunk_content,
                    language=language,
                )
            )

        if end_idx == total_lines:
            break

        start_idx += step

    return chunks