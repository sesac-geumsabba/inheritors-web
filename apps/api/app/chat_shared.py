"""LLM provider(Ollama/OpenAI)와 무관한 챗봇 공용 로직 — DB 저장, MCP 라우팅, SSE 스트리밍.

routers/chat_router.py(Ollama, /chat)와 routers/chat_openai_router.py(OpenAI, /chat/openai)가
이 모듈을 그대로 가져다 쓴다. 두 라우터의 차이는 packages.rag.chains vs openai_chains에서
stream_answer/continue_answer를 어디서 가져오느냐뿐이고, 검색/저장/스트리밍 방식은 완전히 같다.
"""

import json
from collections.abc import Iterator

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.mcp_agent import select_and_run
from packages.rag.retriever import RetrievedChunk, to_vector_literal

# ponytail: 답변을 한 번에 다 쏟아내면 채팅창에서 읽기 피로도가 커서, 문장이 끝나는 시점(마침표)에
# 한 번 멈추고 "네, 더 설명해주세요"로 이어보게 한다. LLM 생성 자체를 여기서 끊기 때문에(for
# 루프를 break) 뒤에 남은 긴 인용 블록까지 기다릴 필요가 없어 응답이 훨씬 빨리 끝난다.
# 처음 400으로 잡았을 때 한 턴에 보이는 답변이 문맥을 다 못 담고(문장 하나 반쯤에서 끊기는
# 느낌) 다음 턴으로 이어져서 대화 흐름이 뚝뚝 끊긴다는 피드백으로 800으로 올림 — 여전히
# 감으로 정한 값이라 실사용 피드백 쌓이면 다시 조정.
PAGE_CHAR_LIMIT = 800
_SENTENCE_END = (".", "!", "?")


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


_MCP_TOOL_LABEL = {"search_law": "법령", "search_decisions": "판례"}


def _mcp_reason(tool_calls_used: list[dict]) -> str:
    """LLM이 실제로 mcp_client에 넘긴 (도구, 검색어) 목록을 사람이 읽을 한 줄로 요약.

    LLM의 판단 근거 자체(자유 서술)는 tool-calling 응답에 들어있지 않아 만들어낼 수
    없으므로, 대신 실제로 무엇을 검색했는지를 보여준다 — "왜 호출됐는지"를 확인할 수
    있는 가장 정확한 근거는 어떤 검색어로 어떤 도구를 호출했는가이기 때문.
    """
    if not tool_calls_used:
        return ""
    parts = [
        f"{_MCP_TOOL_LABEL.get(c['tool'], c['tool'])} '{c['query']}'" for c in tool_calls_used
    ]
    return " · ".join(parts) + " 검색을 위해 호출"


async def fetch_external_sources(query: str) -> tuple[list[dict], bool, dict]:
    """질의를 분석해 korean-law-mcp 호출 여부/도구/검색어를 LLM이 판단하고 실행한다.

    반환하는 precedent_only=True는 "판례 도구만 선택됐고 실제 판례 결과도 있었다"는
    뜻으로, 이때만 내부 RAG를 스킵한다 — 판례 도구를 선택했더라도 결과가 없으면(호출
    실패/0건) 내부 RAG를 폴백으로 계속 써야 답변 근거가 사라지지 않는다.

    mcp_meta는 MCP 호출 여부/도구/호출 이유를 프론트에 보여주기 위한 정보다. MCP 호출이
    실패하거나 0건이라 sources에서 걸러져도 mcp_meta["called"]는 True로 남아있어, "MCP를
    호출은 했다"는 사실 자체를 프론트에서 확인할 수 있다.
    """
    sources, called_tools, tool_calls_used = await select_and_run(query)

    has_case_law_source = any(s.get("source_type") == "case_law" for s in sources)
    precedent_only = (
        "search_decisions" in called_tools
        and "search_law" not in called_tools
        and has_case_law_source
    )

    mcp_meta = {
        "called": bool(called_tools),
        "tools": sorted(called_tools),
        "reason": _mcp_reason(tool_calls_used),
    }
    return sources, precedent_only, mcp_meta


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
    mcp_meta: dict | None = None,
) -> Iterator[str]:
    """토큰을 SSE로 흘려보내다 문장이 끝나는 시점에 budget을 넘기면 생성을 끊고
    "더 설명해드릴까요?"를 붙인 뒤 이어쓰기용 event를 보낸다. /chat, /chat/openai가 공유.
    """
    if emit_sources:
        sse_sources = _sse_sources(chunks, external_sources)
        yield f"event: sources\ndata: {json.dumps(sse_sources, ensure_ascii=False)}\n\n"
        # 프론트에서 "참고 문서" 카드 바로 아래에 MCP 호출 여부/이유를 보여주기 위한 이벤트 —
        # MCP 호출이 실패/0건이라 sources에 아무것도 안 남아도 called는 True로 남아있어야
        # "호출은 했다"를 확인할 수 있어 sources와 분리된 별도 이벤트로 보낸다.
        status = mcp_meta or {"called": False, "tools": [], "reason": ""}
        yield f"event: mcp_status\ndata: {json.dumps(status, ensure_ascii=False)}\n\n"

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
