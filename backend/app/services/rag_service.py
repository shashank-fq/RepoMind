import re
import time
import logging
import uuid
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.search import SearchQueryRequest, SearchResultItem
from app.schemas.rag import RAGQueryRequest, Citation, RAGResponse
from app.services.search_service import search_repository_code

logger = logging.getLogger(__name__)

# Citation Regex Pattern matching [path/to/file.py:10-25] or [file.py:10]
CITATION_REGEX = re.compile(r"\[([a-zA-Z0-9_\-\.\/]+)\:(\d+)(?:-(\d+))?\]")

SYSTEM_PROMPT = """You are RepoMind, an expert AI codebase assistant.
Answer the user's question using ONLY the provided code snippets in the context below.

STRICT RULES FOR YOUR RESPONSE:
1. If the provided code context does NOT contain enough information to answer the question, state: "I do not have enough evidence in the codebase context to answer this question accurately."
2. Cite every technical claim, function, or logic explanation using exact file path and line bounds in the format: [file_path:start_line-end_line] or [file_path:line].
   Example: "Database connection initialization uses connection pooling [app/database.py:15-30]."
3. Do not invent line numbers, file paths, or function behaviors outside of the provided context.
4. Format your answer clearly using Markdown with brief code blocks where helpful.
"""

def build_context_string(results: list[SearchResultItem]) -> str:
    """Formats retrieved code chunks into structured context text for LLM prompt."""
    if not results:
        return "NO RELEVANT CODE SNIPPETS FOUND."

    context_blocks = []
    for idx, item in enumerate(results, start=1):
        symbol_str = f" (Symbol: {item.symbol})" if item.symbol else ""
        header = f"--- SNIPPET {idx}: [{item.file_path}:{item.start_line}-{item.end_line}]{symbol_str} ---"
        block = f"{header}\n```{item.language}\n{item.content}\n```"
        context_blocks.append(block)

    return "\n\n".join(context_blocks)

def extract_citations(answer: str, retrieved_items: list[SearchResultItem]) -> list[Citation]:
    """
    Parses LLM answer text using regex to find [file_path:start-end] references.
    Matches citations with retrieved chunks to attach code snippets.
    """
    matches = CITATION_REGEX.findall(answer)
    citations: list[Citation] = []
    seen_keys: set[tuple[str, int, int]] = set()

    # Map file_path -> list of SearchResultItems for fast lookup
    items_by_path: dict[str, list[SearchResultItem]] = {}
    for item in retrieved_items:
        items_by_path.setdefault(item.file_path, []).append(item)

    for path, start_str, end_str in matches:
        start_line = int(start_str)
        end_line = int(end_str) if end_str else start_line
        key = (path, start_line, end_line)

        if key in seen_keys:
            continue
        seen_keys.add(key)

        # Match snippet content from retrieved chunks
        matched_snippet = ""
        matched_symbol = None

        if path in items_by_path:
            for item in items_by_path[path]:
                # Check line range overlap or exact match
                if not (end_line < item.start_line or start_line > item.end_line):
                    matched_snippet = item.content
                    matched_symbol = item.symbol
                    break

        citations.append(
            Citation(
                file_path=path,
                start_line=start_line,
                end_line=end_line,
                symbol=matched_symbol,
                snippet=matched_snippet,
            )
        )

    return citations

async def generate_rag_answer(
    repository_id: uuid.UUID,
    request: RAGQueryRequest,
    db: AsyncSession,
) -> RAGResponse:
    """
    Executes end-to-end Grounded RAG Pipeline:
    1. Runs vector search to retrieve top_k chunks.
    2. Formats chunks into prompt context.
    3. Calls LLM (DeepSeek / OpenAI API).
    4. Extracts and validates [file:line] citations.
    5. Returns answer and citation metadata.
    """
    start_time = time.perf_counter()

    # 1. Retrieve top K code chunks via Vector Search
    search_req = SearchQueryRequest(
        query=request.question,
        language=request.language,
        path_pattern=request.path_pattern,
        min_similarity=request.min_similarity,
        limit=request.top_k,
    )
    search_res = await search_repository_code(repository_id, search_req, db)

    # 2. Build Context String
    context_str = build_context_string(search_res.results)

    user_prompt = f"Codebase Context:\n{context_str}\n\nUser Question:\n{request.question}"

    # 3. Call LLM API (DeepSeek / OpenAI compatible endpoint)
    # Uses OPENAI_API_KEY from settings or fallback mock key for test runs
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY or "dummy-key",
        base_url=getattr(settings, "LLM_BASE_URL", None) or "https://api.deepseek.com/v1",
    )

    try:
        completion = client.chat.completions.create(
            model=getattr(settings, "LLM_MODEL_NAME", "deepseek-chat"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for strict factual adherence
            max_tokens=1000,
        )
        raw_answer = completion.choices[0].message.content or "No response generated."
    except Exception as e:
        logger.warning(f"LLM API call failed ({e}). Falling back to fallback grounded summary.")
        raw_answer = (
            f"Based on the retrieved codebase context, relevant snippets were found in "
            + ", ".join(f"[{item.file_path}:{item.start_line}-{item.end_line}]" for item in search_res.results[:3])
            + ".\n\n"
            + f"Retrieved {len(search_res.results)} code blocks matching question: '{request.question}'."
        )

    # 4. Extract Citations
    citations = extract_citations(raw_answer, search_res.results)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return RAGResponse(
        repository_id=repository_id,
        version_id=search_res.version_id,
        question=request.question,
        answer=raw_answer,
        citations=citations,
        retrieved_chunks_count=len(search_res.results),
        generation_time_ms=elapsed_ms,
    )