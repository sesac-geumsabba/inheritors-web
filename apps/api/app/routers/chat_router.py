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
_LAW_KEYWORDS = ["법", "조문", "신탁", "상속", "증여", "유류분"]

# ponytail: 법제처 검색 API는 공백구분 키워드를 AND로 처리해서 자연어 질문을 그대로 넣으면
# 거의 항상 0건 (실측 확인). "유언대용신탁과 유류분" 같은 압축 표현도 실패하고,
# "신탁 유류분"처럼 기본 법률용어로 쪼개야 매칭됨 — 분류용 키워드와 별도로 검색어 후보를 둔다.
# search_law(법령명 검색)에 "판례"/"대법원" 같은 판례 전용어를 섞으면 그것도 0건이 돼서
# (실측 확인) 도메인별로 후보 단어 집합을 분리한다. search_law는 법령 "제목" 매칭이라
# "유류분"처럼 실제 법령명에 안 쓰이는 단어를 AND로 섞으면 여전히 0건이라
# (실측: "신탁 유류분"도 실패) 첫 매칭어 하나만 사용 — search_decisions(판례 전문검색)는
# 여러 단어 AND가 오히려 정확도를 높여서 그대로 둠.
_LAW_SEARCH_TERMS = ["신탁", "상속", "증여", "유류분", "수익자", "위탁자"]
_PRECEDENT_SEARCH_TERMS = _LAW_SEARCH_TERMS + ["판례", "대법원", "지방법원"]


def _build_mcp_query(query: str, terms: list[str], max_terms: int | None = None) -> str:
    matched = [t for t in terms if t in query]
    return " ".join(matched[:max_terms] if max_terms else matched) if matched else query


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
        tasks.append(mcp_client.search_law(_build_mcp_query(query, _LAW_SEARCH_TERMS, max_terms=1)))
    if is_precedent:
        mcp_query = _build_mcp_query(query, _PRECEDENT_SEARCH_TERMS)
        tasks.append(mcp_client.search_decisions(mcp_query))

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
    # ponytail: 판례 질의는 내부 DB(신탁 상품설명서/계약서)에 판례 원문이 없어서 검색해봐야
    # "유류분" 등 비슷한 단어가 들어간 상품 안내 문구만 걸림 — MCP 실제 판례를 우선하고
    # 내부 검색은 스킵. 신탁 상품/법령 질의는 기존대로 내부 문서를 계속 사용.
    is_precedent_only = any(k in req.message for k in _PRECEDENT_KEYWORDS)
    tokens, chunks = stream_answer(
        db,
        req.message,
        query_embedding,
        external_sources=external_sources,
        skip_internal=is_precedent_only,
    )

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
