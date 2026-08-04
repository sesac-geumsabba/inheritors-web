import asyncio
import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.chat import ChatRequest
from app.db import get_db
from app.mcp_client import KoreanLawMCPClient
from packages.rag.chains import stream_answer
from packages.rag.embeddings import embed_query
from packages.rag.retriever import RetrievedChunk, to_vector_literal

router = APIRouter(prefix="/chat", tags=["Chat"])
mcp_client = KoreanLawMCPClient()

_PRECEDENT_KEYWORDS = ["판례", "사건", "판결", "대법원", "지방법원"]
_LAW_KEYWORDS = ["법", "조문", "신탁", "상속", "증여"]


def _create_session(db: Session) -> int:
    session_id = db.execute(
        text("INSERT INTO chat_sessions DEFAULT VALUES RETURNING id")
    ).scalar_one()
    db.commit()
    return session_id


def _save_message(
    db: Session, session_id: int, role: str, content: str, embedding: list[float] | None
) -> int:
    embedding_literal = to_vector_literal(embedding) if embedding is not None else None
    message_id = db.execute(
        text(
            "INSERT INTO chat_messages (session_id, role, content, embedding) "
            "VALUES (:session_id, :role, :content, CAST(:embedding AS vector)) RETURNING id"
        ),
        {"session_id": session_id, "role": role, "content": content, "embedding": embedding_literal},
    ).scalar_one()
    db.commit()
    return message_id


def _save_internal_sources(db: Session, message_id: int, chunks: list[RetrievedChunk]) -> None:
    for rank, chunk in enumerate(chunks, start=1):
        db.execute(
            text(
                "INSERT INTO message_sources (message_id, source_type, chunk_id, title, score, rank) "
                "VALUES (:message_id, 'internal_chunk', :chunk_id, :title, :score, :rank)"
            ),
            {
                "message_id": message_id,
                "chunk_id": chunk.chunk_id,
                "title": chunk.file_name,
                "score": chunk.score,
                "rank": rank,
            },
        )
    db.commit()


def _save_external_sources(db: Session, message_id: int, sources: list[dict]) -> None:
    for rank, s in enumerate(sources, start=1):
        db.execute(
            text(
                "INSERT INTO message_sources (message_id, source_type, title, url, snippet, score, rank) "
                "VALUES (:message_id, :source_type, :title, :url, :snippet, :score, :rank)"
            ),
            {
                "message_id": message_id,
                "source_type": s["source_type"],
                "title": s.get("title", ""),
                "url": s.get("url") or None,
                "snippet": s.get("snippet", ""),
                "score": s.get("score"),
                "rank": rank,
            },
        )
    db.commit()


async def _fetch_external_sources(query: str) -> list[dict]:
    """판례/법령 관련 질의로 보이면 korean-law-mcp를 병렬 호출. 관련 없어 보이면 스킵."""
    is_precedent = any(k in query for k in _PRECEDENT_KEYWORDS)
    is_law = any(k in query for k in _LAW_KEYWORDS)
    if not is_precedent and not is_law:
        return []

    tasks = []
    if is_law:
        tasks.append(mcp_client.search_law(query))
    if is_precedent:
        tasks.append(mcp_client.search_decisions(query))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    sources: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        # mcp_client는 오류/결과없음도 score=0.0 항목으로 반환 — 답변 근거로 못 쓰니 걸러냄
        sources.extend(s for s in r if s.get("score", 0) > 0)
    return sources


@router.post("")
async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    session_id = req.session_id or _create_session(db)
    query_embedding = embed_query(req.message)
    _save_message(db, session_id, "user", req.message, query_embedding)

    external_sources = await _fetch_external_sources(req.message)
    tokens, chunks = stream_answer(db, req.message, query_embedding, external_sources=external_sources)

    def event_stream() -> Iterator[str]:
        sse_sources = [
            {
                "source_type": "internal_chunk",
                "title": c.file_name,
                "page": c.page,
                "url": None,
                "score": round(c.score, 3),
                "snippet": c.content[:120],
            }
            for c in chunks
        ] + [
            {
                "source_type": s["source_type"],
                "title": s.get("title", ""),
                "page": None,
                "url": s.get("url") or None,
                "score": s.get("score"),
                "snippet": s.get("snippet", "")[:200],
            }
            for s in external_sources
        ]
        yield f"event: sources\ndata: {json.dumps(sse_sources, ensure_ascii=False)}\n\n"

        parts: list[str] = []
        for token in tokens:
            parts.append(token)
            # SSE는 data 라인 안에 개행이 오면 각 줄마다 "data: "를 다시 붙여야 한다.
            yield "data: " + token.replace("\n", "\ndata: ") + "\n\n"

        message_id = _save_message(db, session_id, "assistant", "".join(parts), None)
        _save_internal_sources(db, message_id, chunks)
        _save_external_sources(db, message_id, external_sources)
        yield f"event: done\ndata: {{\"session_id\": {session_id}}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
