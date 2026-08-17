from dataclasses import dataclass

@dataclass
class RawChunkData:
    start_line: int
    end_line: int
    symbol: str | None
    content: str
    language: str