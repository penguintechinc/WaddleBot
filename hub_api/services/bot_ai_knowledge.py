"""AI Knowledge service -- ports `aiKnowledgeService.js` + `aiKnowledgeController.js`.

Knowledge-source CRUD, content crawling (GitHub Contents API / sitemap.xml
+ HTML strip), chunking, Ollama embeddings/completions, pgvector
similarity search, and AI-generated support-ticket suggestions. Faithful
port: same chunk sizing, same confidence threshold, same regex-based
HTML extraction the Node version used (a rewrite to a real HTML parser
is out of scope for a 1:1 behavior port -- migration plan §1 non-goals).

pydal has no pgvector field type, so the two `ai_knowledge_chunks`
operations that touch `embedding` (`vector(384)`, cosine `<=>` operator)
run as raw SQL via `dal.executesql` -- everything else goes through
pydal's query builder against `bot_tables.py`'s bindings.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_CHUNK_SIZE_TOKENS = 500
_CHUNK_OVERLAP_TOKENS = 50
_CHARS_PER_TOKEN = 4
_CHUNK_SIZE_CHARS = _CHUNK_SIZE_TOKENS * _CHARS_PER_TOKEN
_CHUNK_OVERLAP_CHARS = _CHUNK_OVERLAP_TOKENS * _CHARS_PER_TOKEN

_SUGGESTION_CONFIDENCE_THRESHOLD = 0.7
_DEFAULT_TOP_K = 5

_VALID_SOURCE_TYPES = {
    "github_wiki",
    "github_repo_markdown",
    "mkdocs",
    "docusaurus",
    "generic_url",
    "manual",
}
_VALID_FEEDBACK = {"helpful", "not_helpful"}


class KnowledgeServiceError(Exception):
    """Carries an HTTP status, mirroring Node's `Object.assign(new Error(...), {status})`."""

    def __init__(self, message: str, status: int = 500) -> None:
        """Store `status` alongside the standard `Exception` message."""
        super().__init__(message)
        self.status = status


def _ollama_base_url() -> str:
    return os.environ.get("OLLAMA_URL", "http://localhost:11434")


def _embed_model() -> str:
    return os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def _llm_model() -> str:
    return os.environ.get("OLLAMA_LLM_MODEL", "llama3.2:3b")


# ── Embedding & LLM helpers ──────────────────────────────────────────────


async def _generate_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient(base_url=_ollama_base_url(), timeout=30.0) as client:
        response = await client.post(
            "/api/embeddings", json={"model": _embed_model(), "prompt": text}
        )
    response.raise_for_status()
    data = response.json()
    result: list[float] = data["embedding"]
    return result


async def _generate_completion(prompt: str) -> str:
    async with httpx.AsyncClient(base_url=_ollama_base_url(), timeout=60.0) as client:
        response = await client.post(
            "/api/generate",
            json={"model": _llm_model(), "prompt": prompt, "stream": False},
        )
    response.raise_for_status()
    data = response.json()
    result: str = data["response"]
    return result


# ── Text chunking ────────────────────────────────────────────────────────


@dataclass(slots=True)
class _Chunk:
    content: str
    chunk_index: int
    token_count: int


def _chunk_text(text: str) -> list[_Chunk]:
    chunks: list[_Chunk] = []
    offset = 0
    index = 0
    length = len(text)
    while offset < length:
        end = min(offset + _CHUNK_SIZE_CHARS, length)
        content = text[offset:end].strip()
        if content:
            chunks.append(
                _Chunk(
                    content=content,
                    chunk_index=index,
                    token_count=-(-len(content) // _CHARS_PER_TOKEN),  # ceil div
                )
            )
            index += 1
        if end == length:
            break
        offset = end - _CHUNK_OVERLAP_CHARS
    return chunks


# ── Content fetchers ─────────────────────────────────────────────────────


@dataclass(slots=True)
class _Page:
    url: str
    title: str
    content: str


async def _fetch_github_markdown(
    source_url: str, branch: str, docs_path: str, token: str | None
) -> list[_Page]:
    match = re.search(r"github\.com/([^/]+/[^/]+)", source_url)
    repo_path = (
        match.group(1).removesuffix(".git")
        if match
        else re.sub(r"^https?://github\.com/", "", source_url).removesuffix(".git")
    )
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    normalized_path = docs_path[1:] if docs_path.startswith("/") else docs_path
    contents_url = (
        f"https://api.github.com/repos/{repo_path}/contents/{normalized_path}?ref={branch}"
    )

    pages: list[_Page] = []

    async def crawl(url: str, client: httpx.AsyncClient) -> None:
        response = await client.get(url, headers=headers)
        if response.is_error:
            logger.warning("GitHub API non-OK response url=%s status=%s", url, response.status_code)
            return
        items = response.json()

        if not isinstance(items, list):
            if items.get("type") == "file" and items.get("name", "").endswith(".md"):
                import base64

                decoded = base64.b64decode(items["content"]).decode("utf-8")
                pages.append(
                    _Page(
                        url=items["html_url"],
                        title=items["name"].removesuffix(".md").replace("-", " "),
                        content=decoded,
                    )
                )
            return

        for item in items:
            if item.get("type") == "dir":
                await crawl(item["url"], client)
            elif item.get("type") == "file" and item.get("name", "").endswith(".md"):
                file_response = await client.get(item["url"], headers=headers)
                if file_response.is_error:
                    continue
                import base64

                file_data = file_response.json()
                decoded = base64.b64decode(file_data["content"]).decode("utf-8")
                pages.append(
                    _Page(
                        url=item["html_url"],
                        title=item["name"].removesuffix(".md").replace("-", " "),
                        content=decoded,
                    )
                )

    async with httpx.AsyncClient(timeout=30.0) as client:
        await crawl(contents_url, client)
    return pages


_TITLE_RE = re.compile(r"<title>([^<]+)</title>", re.IGNORECASE)
_MAIN_RE = re.compile(r"<main[^>]*>([\s\S]*?)</main>", re.IGNORECASE)
_ARTICLE_RE = re.compile(r"<article[^>]*>([\s\S]*?)</article>", re.IGNORECASE)
_BODY_RE = re.compile(r"<body[^>]*>([\s\S]*?)</body>", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<script[^>]*>[\s\S]*?</script>", re.IGNORECASE)
_STYLE_RE = re.compile(r"<style[^>]*>[\s\S]*?</style>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_LOC_RE = re.compile(r"<loc>([^<]+)</loc>")

_CRAWLER_UA = {"User-Agent": "WaddleBot/2.0 Knowledge Indexer"}


async def _fetch_sitemap_pages(base_url: str) -> list[_Page]:
    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    pages: list[_Page] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            sitemap_response = await client.get(sitemap_url, headers=_CRAWLER_UA)
        except httpx.HTTPError as exc:
            logger.warning("Could not fetch sitemap sitemap_url=%s err=%s", sitemap_url, exc)
            return pages

        if sitemap_response.is_error:
            logger.warning(
                "Sitemap not found, skipping sitemap_url=%s status=%s",
                sitemap_url,
                sitemap_response.status_code,
            )
            return pages

        page_urls = [m.strip() for m in _LOC_RE.findall(sitemap_response.text)]

        for page_url in page_urls:
            try:
                response = await client.get(page_url, headers=_CRAWLER_UA)
                if response.is_error:
                    continue
                html = response.text
                title_match = _TITLE_RE.search(html)
                title = title_match.group(1).strip() if title_match else page_url

                main_match = (
                    _MAIN_RE.search(html) or _ARTICLE_RE.search(html) or _BODY_RE.search(html)
                )
                if not main_match:
                    continue

                text = _SCRIPT_RE.sub("", main_match.group(1))
                text = _STYLE_RE.sub("", text)
                text = _TAG_RE.sub(" ", text)
                text = _WHITESPACE_RE.sub(" ", text).strip()

                if len(text) > 100:
                    pages.append(_Page(url=page_url, title=title, content=text))
            except httpx.HTTPError as exc:
                logger.warning("Failed to fetch knowledge page page_url=%s err=%s", page_url, exc)

    return pages


# ── DTOs ──────────────────────────────────────────────────────────────────


@dataclass(slots=True, frozen=True)
class KnowledgeSourceCreate:
    """Request DTO for `POST .../ai-knowledge/sources`."""

    source_name: str
    source_type: str
    community_id: int | None = None
    vendor_id: int | None = None
    module_id: int | None = None
    source_url: str | None = None
    branch: str = "main"
    docs_path: str = "/"
    refresh_interval: str = "weekly"
    encrypted_token: str | None = None


@dataclass(slots=True)
class KnowledgeSource:
    """Response DTO -- one `ai_knowledge_sources` row."""

    id: int
    community_id: int | None
    vendor_id: int | None
    module_id: int | None
    source_name: str
    source_type: str
    source_url: str | None
    branch: str
    docs_path: str
    refresh_interval: str
    is_active: bool
    last_indexed_at: str | None
    indexed_page_count: int
    index_errors: str | None
    created_at: str | None
    updated_at: str | None


@dataclass(slots=True)
class KnowledgeSearchResult:
    """One scored chunk from `search_knowledge`."""

    chunk_id: int
    source_id: int
    content: str
    source_url: str | None
    source_title: str | None
    chunk_index: int
    token_count: int | None
    score: float


@dataclass(slots=True)
class TicketSuggestion:
    """A row from `ai_ticket_suggestions`."""

    id: int
    ticket_id: int
    suggestion_text: str
    confidence_score: float
    cited_chunks: list[int] = field(default_factory=list)
    feedback: str | None = None
    is_auto_posted: bool = False
    created_at: str | None = None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _to_source(row: Any) -> KnowledgeSource:
    return KnowledgeSource(
        id=row.id,
        community_id=row.community_id,
        vendor_id=row.vendor_id,
        module_id=row.module_id,
        source_name=row.source_name,
        source_type=row.source_type,
        source_url=row.source_url,
        branch=row.branch,
        docs_path=row.docs_path,
        refresh_interval=row.refresh_interval,
        is_active=bool(row.is_active),
        last_indexed_at=_iso(row.last_indexed_at),
        indexed_page_count=row.indexed_page_count or 0,
        index_errors=row.index_errors,
        created_at=_iso(row.created_at),
        updated_at=_iso(row.updated_at),
    )


# ── Source management ────────────────────────────────────────────────────


def add_knowledge_source(dal: Any, payload: KnowledgeSourceCreate) -> KnowledgeSource:
    """`POST .../ai-knowledge/sources` -- caller triggers `index_source` after, if not `manual`."""
    if not payload.source_name.strip():
        raise KnowledgeServiceError("source_name is required", status=400)
    if payload.source_type not in _VALID_SOURCE_TYPES:
        raise KnowledgeServiceError(
            f"source_type must be one of: {', '.join(sorted(_VALID_SOURCE_TYPES))}", status=400
        )

    new_id = dal.ai_knowledge_sources.insert(
        community_id=payload.community_id,
        vendor_id=payload.vendor_id,
        module_id=payload.module_id,
        source_name=payload.source_name.strip(),
        source_type=payload.source_type,
        source_url=payload.source_url,
        branch=payload.branch,
        docs_path=payload.docs_path,
        refresh_interval=payload.refresh_interval,
        encrypted_token=payload.encrypted_token,
        is_active=True,
    )
    dal.commit()
    return _to_source(dal.ai_knowledge_sources[new_id])


def list_knowledge_sources(dal: Any, community_id: int | None = None) -> list[KnowledgeSource]:
    """`GET .../ai-knowledge/sources`, optionally filtered by `?communityId=`."""
    query = dal.ai_knowledge_sources.id > 0
    if community_id is not None:
        query &= dal.ai_knowledge_sources.community_id == community_id
    rows = dal(query).select(orderby=dal.ai_knowledge_sources.source_name)
    return [_to_source(row) for row in rows]


_ALLOWED_UPDATE_FIELDS = {
    "source_name",
    "source_url",
    "branch",
    "docs_path",
    "refresh_interval",
    "encrypted_token",
    "is_active",
}


def update_knowledge_source(dal: Any, source_id: int, updates: dict[str, Any]) -> KnowledgeSource:
    """`PUT .../ai-knowledge/sources/:id` -- only `_ALLOWED_UPDATE_FIELDS` are writable."""
    fields = {k: v for k, v in updates.items() if k in _ALLOWED_UPDATE_FIELDS}
    if not fields:
        raise KnowledgeServiceError("No valid fields provided for update", status=400)

    row = dal.ai_knowledge_sources[source_id]
    if row is None:
        raise KnowledgeServiceError("Knowledge source not found", status=404)
    dal(dal.ai_knowledge_sources.id == source_id).update(**fields)
    dal.commit()
    return _to_source(dal.ai_knowledge_sources[source_id])


def delete_knowledge_source(dal: Any, source_id: int) -> None:
    """`DELETE .../ai-knowledge/sources/:id` -- chunks cascade via the DB FK."""
    row = dal.ai_knowledge_sources[source_id]
    if row is None:
        raise KnowledgeServiceError("Knowledge source not found", status=404)
    dal(dal.ai_knowledge_sources.id == source_id).delete()
    dal.commit()


# ── Indexing ──────────────────────────────────────────────────────────────


def _upsert_chunk(
    dal: Any,
    *,
    source_id: int,
    content: str,
    content_hash: str,
    source_url: str,
    source_title: str,
    chunk_index: int,
    embedding: list[float],
    token_count: int,
) -> None:
    """Raw SQL: `ai_knowledge_chunks.embedding` is pgvector, outside pydal's field types."""
    embedding_literal = "[" + ",".join(str(v) for v in embedding) + "]"
    dal.executesql(
        """
        INSERT INTO ai_knowledge_chunks
            (source_id, content, content_hash, source_url, source_title,
             chunk_index, embedding, token_count, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, NOW())
        ON CONFLICT (source_id, content_hash) DO UPDATE SET
            source_url = EXCLUDED.source_url,
            source_title = EXCLUDED.source_title,
            chunk_index = EXCLUDED.chunk_index,
            embedding = EXCLUDED.embedding,
            token_count = EXCLUDED.token_count,
            updated_at = NOW()
        """,
        placeholders=[
            source_id,
            content,
            content_hash,
            source_url,
            source_title,
            chunk_index,
            embedding_literal,
            token_count,
        ],
    )


async def index_source(dal: Any, source_id: int) -> None:
    """Fetch content, chunk it, embed each chunk, upsert into `ai_knowledge_chunks`.

    Fire-and-forget from the caller's perspective (the route responds
    before this completes, matching Node's `reindexSource`/
    `addKnowledgeSource`'s `setImmediate`/uncaught-promise pattern) --
    invoked via `asyncio.create_task` by `blueprints/v1/bot.py`.
    """
    source = dal.ai_knowledge_sources[source_id]
    if source is None:
        raise KnowledgeServiceError(f"Knowledge source {source_id} not found", status=404)

    dal(dal.ai_knowledge_sources.id == source_id).update(index_errors=None)
    dal.commit()

    pages: list[_Page] = []
    try:
        if source.source_type in ("github_wiki", "github_repo_markdown"):
            pages = await _fetch_github_markdown(
                source.source_url, source.branch, source.docs_path, source.encrypted_token
            )
        elif source.source_type in ("mkdocs", "docusaurus", "generic_url"):
            pages = await _fetch_sitemap_pages(source.source_url)
        elif source.source_type == "manual":
            logger.info("Manual source -- skipping crawl source_id=%s", source_id)
            return
        else:
            raise KnowledgeServiceError(f"Unknown source_type: {source.source_type}")
    except Exception as exc:  # noqa: BLE001 - persisted as index_errors, matching Node
        dal(dal.ai_knowledge_sources.id == source_id).update(index_errors=str(exc))
        dal.commit()
        raise

    total_chunks = 0
    errors: list[str] = []

    for page in pages:
        for chunk in _chunk_text(page.content):
            try:
                content_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
                embedding = await _generate_embedding(chunk.content)
                _upsert_chunk(
                    dal,
                    source_id=source_id,
                    content=chunk.content,
                    content_hash=content_hash,
                    source_url=page.url,
                    source_title=page.title,
                    chunk_index=chunk.chunk_index,
                    embedding=embedding,
                    token_count=chunk.token_count,
                )
                total_chunks += 1
            except Exception as exc:  # noqa: BLE001 - per-chunk error, matches Node's per-chunk try/catch
                errors.append(f"{page.url}: {exc}")
                logger.warning(
                    "Chunk index error source_id=%s url=%s err=%s", source_id, page.url, exc
                )

    dal.commit()
    dal(dal.ai_knowledge_sources.id == source_id).update(
        last_indexed_at=datetime.utcnow(),
        indexed_page_count=len(pages),
        index_errors="\n".join(errors[:10]) if errors else None,
    )
    dal.commit()
    logger.info(
        "Knowledge source indexed source_id=%s pages=%s chunks=%s",
        source_id,
        len(pages),
        total_chunks,
    )


# ── Search & suggestions ────────────────────────────────────────────────


async def search_knowledge(
    dal: Any,
    query_text: str,
    *,
    community_id: int | None = None,
    vendor_id: int | None = None,
    top_k: int = _DEFAULT_TOP_K,
) -> list[KnowledgeSearchResult]:
    """Vector similarity search (raw SQL -- pgvector `<=>` cosine distance)."""
    if not query_text or not query_text.strip():
        raise KnowledgeServiceError("Query text is required", status=400)

    embedding = await _generate_embedding(query_text.strip())
    embedding_literal = "[" + ",".join(str(v) for v in embedding) + "]"

    conditions = ["ks.is_active = true"]
    filter_params: list[Any] = []
    if community_id is not None:
        conditions.append("ks.community_id = %s")
        filter_params.append(community_id)
    if vendor_id is not None:
        conditions.append("ks.vendor_id = %s")
        filter_params.append(vendor_id)
    where = " AND ".join(conditions)

    # Placeholder order must match the SQL's %s occurrences left to right:
    # score-clause embedding, WHERE-clause filters, ORDER BY embedding, LIMIT.
    placeholders = [embedding_literal, *filter_params, embedding_literal, top_k]

    sql = f"""
        SELECT kc.id, kc.source_id, kc.content, kc.source_url, kc.source_title,
               kc.chunk_index, kc.token_count,
               1 - (kc.embedding <=> %s::vector) AS score
        FROM ai_knowledge_chunks kc
        JOIN ai_knowledge_sources ks ON ks.id = kc.source_id
        WHERE {where}
        ORDER BY kc.embedding <=> %s::vector
        LIMIT %s
    """  # noqa: S608 - `where` only ever interpolates the hardcoded literal fragments above;
    # every value (community_id, vendor_id, top_k, embedding) is parameterized via `placeholders`
    rows = dal.executesql(sql, placeholders=placeholders)

    return [
        KnowledgeSearchResult(
            chunk_id=row[0],
            source_id=row[1],
            content=row[2],
            source_url=row[3],
            source_title=row[4],
            chunk_index=row[5],
            token_count=row[6],
            score=float(row[7]),
        )
        for row in rows
    ]


async def generate_suggestion(
    dal: Any, ticket_id: int, ticket_text: str, *, community_id: int | None = None
) -> TicketSuggestion | None:
    """`POST .../ai-knowledge/suggest` -- `None` if top result is below the confidence threshold."""
    results = await search_knowledge(
        dal, ticket_text, community_id=community_id, top_k=_DEFAULT_TOP_K
    )

    if not results or results[0].score < _SUGGESTION_CONFIDENCE_THRESHOLD:
        logger.info(
            "Knowledge search below threshold -- no suggestion ticket_id=%s top_score=%s",
            ticket_id,
            results[0].score if results else 0,
        )
        return None

    top_chunks = [r for r in results if r.score >= _SUGGESTION_CONFIDENCE_THRESHOLD]
    confidence_score = top_chunks[0].score

    context = "\n\n---\n\n".join(
        f'[{i + 1}] From "{r.source_title or r.source_url}":\n{r.content}'
        for i, r in enumerate(top_chunks)
    )
    prompt = (
        "You are a helpful support assistant. Using only the provided knowledge base excerpts, "
        "write a concise, helpful response to the following support ticket. "
        "Cite the source numbers (e.g. [1], [2]) inline where relevant. "
        "If the knowledge base does not contain enough information to answer, say so clearly.\n\n"
        f"Support ticket:\n{ticket_text}\n\n"
        f"Knowledge base:\n{context}\n\n"
        "Response:"
    )

    suggestion_text = (await _generate_completion(prompt)).strip()
    cited_chunk_ids = [r.chunk_id for r in top_chunks]

    new_id = dal.ai_ticket_suggestions.insert(
        ticket_id=ticket_id,
        suggestion_text=suggestion_text,
        confidence_score=round(confidence_score, 3),
        cited_chunks=cited_chunk_ids,
        is_auto_posted=False,
    )
    dal.commit()
    row = dal.ai_ticket_suggestions[new_id]
    return TicketSuggestion(
        id=row.id,
        ticket_id=row.ticket_id,
        suggestion_text=row.suggestion_text,
        confidence_score=row.confidence_score,
        cited_chunks=list(row.cited_chunks or []),
        feedback=row.feedback,
        is_auto_posted=bool(row.is_auto_posted),
        created_at=_iso(row.created_at),
    )


def record_feedback(dal: Any, suggestion_id: int, feedback: str) -> TicketSuggestion:
    """`POST .../ai-knowledge/suggestions/:id/feedback`."""
    if feedback not in _VALID_FEEDBACK:
        raise KnowledgeServiceError(
            f"feedback must be one of: {', '.join(sorted(_VALID_FEEDBACK))}", status=400
        )
    row = dal.ai_ticket_suggestions[suggestion_id]
    if row is None:
        raise KnowledgeServiceError("Suggestion not found", status=404)
    dal(dal.ai_ticket_suggestions.id == suggestion_id).update(feedback=feedback)
    dal.commit()
    row = dal.ai_ticket_suggestions[suggestion_id]
    return TicketSuggestion(
        id=row.id,
        ticket_id=row.ticket_id,
        suggestion_text=row.suggestion_text,
        confidence_score=row.confidence_score,
        cited_chunks=list(row.cited_chunks or []),
        feedback=row.feedback,
        is_auto_posted=bool(row.is_auto_posted),
        created_at=_iso(row.created_at),
    )
