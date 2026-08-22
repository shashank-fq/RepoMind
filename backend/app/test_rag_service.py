import pytest
from app.schemas.search import SearchResultItem
from app.services.rag_service import build_context_string, extract_citations

def test_build_context_string():
    item = SearchResultItem(
        chunk_id="00000000-0000-0000-0000-000000000001",
        file_id="00000000-0000-0000-0000-000000000002",
        file_path="app/auth.py",
        symbol="login",
        language="python",
        start_line=10,
        end_line=20,
        content="def login(): pass",
        similarity_score=0.92,
        distance=0.08,
    )
    context = build_context_string([item])
    assert "app/auth.py:10-20" in context
    assert "Symbol: login" in context
    assert "def login(): pass" in context

def test_extract_citations():
    item = SearchResultItem(
        chunk_id="00000000-0000-0000-0000-000000000001",
        file_id="00000000-0000-0000-0000-000000000002",
        file_path="app/services/ingestion.py",
        symbol="clone_repo",
        language="python",
        start_line=15,
        end_line=30,
        content="def clone_repo(): pass",
        similarity_score=0.88,
        distance=0.12,
    )

    answer_text = "Repository cloning uses GitPython shallow clone [app/services/ingestion.py:15-30]."
    citations = extract_citations(answer_text, [item])

    assert len(citations) == 1
    assert citations[0].file_path == "app/services/ingestion.py"
    assert citations[0].start_line == 15
    assert citations[0].end_line == 30
    assert citations[0].symbol == "clone_repo"