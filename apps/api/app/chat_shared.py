"""LLM provider(Ollama/OpenAI)와 무관한 챗봇 공용 로직 — DB 저장, MCP 라우팅, SSE 스트리밍.

routers/chat_router.py(Ollama, /chat)와 routers/chat_openai_router.py(OpenAI, /chat/openai)가
이 모듈을 그대로 가져다 쓴다. 두 라우터의 차이는 packages.rag.chains vs openai_chains에서
stream_answer/continue_answer를 어디서 가져오느냐뿐이고, 검색/저장/스트리밍 방식은 완전히 같다.
"""

import asyncio
import json
import re
from collections.abc import Iterator

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.mcp_client import mcp_client
from packages.rag.retriever import RetrievedChunk, to_vector_literal

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
# "판례"/"대법원"/"지방법원"은 판례 여부 분류·정확도 보정용 보조어일 뿐 그 자체로는 검색
# 주제가 아니다 — 아래 매칭이 이 보조어만 걸리면(=신탁/상속 밖 질의) _extract_keywords로
# 넘어가야 한다("부동산 재건축 판례" 같은 질의에서 "판례"만 남으면 검색이 무의미해짐, 실측 확인).
_PRECEDENT_BOOST_TERMS = ["판례", "대법원", "지방법원"]
_PRECEDENT_SEARCH_TERMS = _LAW_SEARCH_TERMS + _PRECEDENT_BOOST_TERMS

# ponytail: 신탁/상속 도메인 밖 질의(예: "부동산 재건축 판례")는 위 고정 어휘 목록에 하나도
# 안 걸려서 자연어 원문이 그대로 MCP에 넘어가는데, 법제처 API가 공백 단어를 AND로 묶어
# 대부분 0건이 된다(실측 확인) — 조사/군더더기를 떼고 실제 명사만 남겨서 재시도한다.
# 형태소 분석기 없이 정규식으로 흔한 조사만 떼는 수준이라 완벽하지 않음 — 검색이 계속
# 빗나가면 KoNLPy 등 형태소 분석기 도입 검토.
_QUERY_STOPWORDS = {
    "관련", "대해서", "대해", "대한", "설명해줘", "설명해주세요", "알려줘", "알려주세요",
    "궁금해요", "궁금합니다", "무엇인가요", "무엇", "어떻게", "되나요", "인가요", "좀", "혹시",
    "판례", "판결", "사건", "대법원", "지방법원", "법령",
}
_TRAILING_PARTICLE_RE = re.compile(r"(은|는|이|가|을|를|의|에|에서|으로|로|와|과|도|만)$")


def _extract_keywords(query: str, max_terms: int = 3) -> str:
    keywords = []
    for word in query.split():
        cleaned = _TRAILING_PARTICLE_RE.sub("", word)
        if cleaned and cleaned not in _QUERY_STOPWORDS and len(cleaned) > 1:
            keywords.append(cleaned)
    return " ".join(keywords[:max_terms])

# ponytail: 답변을 한 번에 다 쏟아내면 채팅창에서 읽기 피로도가 커서, 문장이 끝나는 시점(마침표)에
# 한 번 멈추고 "네, 더 설명해주세요"로 이어보게 한다. LLM 생성 자체를 여기서 끊기 때문에(for
# 루프를 break) 뒤에 남은 긴 인용 블록까지 기다릴 필요가 없어 응답이 훨씬 빨리 끝난다.
# 처음 400으로 잡았을 때 한 턴에 보이는 답변이 문맥을 다 못 담고(문장 하나 반쯤에서 끊기는
# 느낌) 다음 턴으로 이어져서 대화 흐름이 뚝뚝 끊긴다는 피드백으로 800으로 올림 — 여전히
# 감으로 정한 값이라 실사용 피드백 쌓이면 다시 조정.
PAGE_CHAR_LIMIT = 800
_SENTENCE_END = (".", "!", "?")


def is_precedent_only(query: str) -> bool:
    return any(k in query for k in _PRECEDENT_KEYWORDS)


def _build_mcp_query(query: str, terms: list[str], max_terms: int | None = None) -> str:
    matched = [t for t in terms if t in query]
    # 실제 주제어(신탁/상속/증여 등)는 하나도 안 걸리고 "판례" 같은 보조어만 걸렸으면
    # 그 보조어 하나로는 검색이 무의미하니 일반 키워드 추출로 넘어간다.
    domain_matched = [t for t in matched if t not in _PRECEDENT_BOOST_TERMS]
    if not domain_matched:
        return _extract_keywords(query) or query
    return " ".join(matched[:max_terms] if max_terms else matched)


def create_session(db: Session) -> int:
    session_id = db.execute(
        text("INSERT INTO chat_sessions DEFAULT VALUES RETURNING id")
    ).scalar_one()
    db.commit()
    return session_id


def save_message(
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


def load_context_for_continue(
    db: Session, message_id: int
) -> tuple[int, str, str, list[RetrievedChunk], list[dict]]:
    """이어쓰기 대상 메시지에서 (session_id, 원 질문, 이전 답변, 내부 청크, 외부 출처)를 복원.

    재검색하지 않고 message_sources에 이미 저장된 근거를 그대로 재사용한다 — 검색은 원 질문
    시점의 것과 동일해야 "이어지는" 답변이 되고, 새로 검색하면 다른 결과가 섞일 수 있다.
    """
    row = db.execute(
        text("SELECT session_id, content FROM chat_messages WHERE id = :id AND role = 'assistant'"),
        {"id": message_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="message not found")
    session_id, previous_answer = row

    user_row = db.execute(
        text(
            "SELECT content FROM chat_messages "
            "WHERE session_id = :sid AND role = 'user' AND id < :mid "
            "ORDER BY id DESC LIMIT 1"
        ),
        {"sid": session_id, "mid": message_id},
    ).first()
    query = user_row[0] if user_row else ""

    chunk_rows = db.execute(
        text(
            "SELECT c.id, c.document_id, c.content, c.page, d.file_name, d.category, d.bank, d.contract_type "
            "FROM message_sources ms "
            "JOIN chunks c ON c.id = ms.chunk_id "
            "JOIN documents d ON d.id = c.document_id "
            "WHERE ms.message_id = :mid AND ms.source_type = 'internal_chunk' "
            "ORDER BY ms.rank"
        ),
        {"mid": message_id},
    ).all()
    chunks = [
        RetrievedChunk(
            chunk_id=r.id,
            document_id=r.document_id,
            content=r.content,
            page=r.page,
            file_name=r.file_name,
            category=r.category,
            bank=r.bank,
            contract_type=r.contract_type,
            score=1.0,
        )
        for r in chunk_rows
    ]

    external_rows = db.execute(
        text(
            "SELECT source_type, title, url, snippet, score FROM message_sources "
            "WHERE message_id = :mid AND source_type != 'internal_chunk' ORDER BY rank"
        ),
        {"mid": message_id},
    ).all()
    external_sources = [dict(r._mapping) for r in external_rows]

    return session_id, query, previous_answer, chunks, external_sources


async def fetch_external_sources(query: str) -> list[dict]:
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


def _sse_sources(chunks: list[RetrievedChunk], external_sources: list[dict]) -> list[dict]:
    return [
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


def event_stream(
    db: Session,
    session_id: int,
    tokens: Iterator[str],
    chunks: list[RetrievedChunk],
    external_sources: list[dict],
    emit_sources: bool,
) -> Iterator[str]:
    """토큰을 SSE로 흘려보내다 문장이 끝나는 시점에 budget을 넘기면 생성을 끊고
    "더 설명해드릴까요?"를 붙인 뒤 이어쓰기용 event를 보낸다. /chat, /chat/openai가 공유.
    """
    if emit_sources:
        sse_sources = _sse_sources(chunks, external_sources)
        yield f"event: sources\ndata: {json.dumps(sse_sources, ensure_ascii=False)}\n\n"

    parts: list[str] = []
    paused_early = False
    try:
        for token in tokens:
            parts.append(token)
            # SSE는 data 라인 안에 개행이 오면 각 줄마다 "data: "를 다시 붙여야 한다.
            yield "data: " + token.replace("\n", "\ndata: ") + "\n\n"
            shown = "".join(parts)
            if len(shown) >= PAGE_CHAR_LIMIT and shown.rstrip().endswith(_SENTENCE_END):
                paused_early = True
                break  # LLM 생성 자체를 여기서 그만 받는다 — 뒤에 남은 긴 인용 블록을 기다리지 않음
    except Exception as e:
        # LLM 연결 끊김/모델 미존재/API 오류 등으로 스트림 중간에 예외가 나면 그대로 두면
        # 응답이 끝맺음 없이 끊겨 브라우저에 ERR_INCOMPLETE_CHUNKED_ENCODING이 뜬다.
        # 여기서 잡아 안내 메시지로 스트림을 정상 종료한다.
        print(f"[error] LLM 스트리밍 실패: {e}")
        fallback = "죄송합니다, 답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        parts = [fallback]
        yield "data: " + fallback + "\n\n"

    if paused_early:
        followup = "\n\n더 설명해드릴까요?"
        parts.append(followup)
        yield "data: " + followup.replace("\n", "\ndata: ") + "\n\n"

    content = "".join(parts)
    message_id = save_message(db, session_id, "assistant", content, None)
    # sources는 항상 저장한다 (emit_sources=False라도) — 이 답변이 또 "더 설명해드릴까요?"로
    # 끊겨서 재이어쓰기 대상이 될 수 있고, 그때 load_context_for_continue가 이 message_sources를
    # 그대로 읽어 근거를 복원한다. SSE로 sources 카드를 다시 보여줄지만 emit_sources로 가른다.
    _save_internal_sources(db, message_id, chunks)
    _save_external_sources(db, message_id, external_sources)
    if paused_early:
        yield f"event: awaiting_continue\ndata: {{\"message_id\": {message_id}}}\n\n"
    yield f"event: done\ndata: {{\"session_id\": {session_id}}}\n\n"
