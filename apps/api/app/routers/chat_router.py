"""기존 Ollama 기반 챗봇 — /prototype/chat 프론트가 호출한다.

검색/MCP/DB 저장/SSE 스트리밍 로직은 app/chat_shared.py에 있고, 여기서는 LLM 호출부만
packages.rag.chains(Ollama)를 쓴다. OpenAI 버전은 routers/chat_openai_router.py 참고.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.chat import ChatRequest, ContinueRequest
from app.chat_shared import (
    create_session,
    event_stream,
    fetch_external_sources,
    load_context_for_continue,
    save_message,
)
from app.db import get_db
from packages.rag.chains import continue_answer, stream_answer
from packages.rag.embeddings import embed_query

router = APIRouter(prefix="/chat", tags=["Chat (Ollama, prototype)"])


@router.post("")
async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    session_id = req.session_id or create_session(db)
    query_embedding = embed_query(req.message)
    save_message(db, session_id, "user", req.message, query_embedding)

    external_sources, precedent_only, mcp_meta = await fetch_external_sources(req.message)
    # ponytail: 판례 질의는 내부 DB(신탁 상품설명서/계약서)에 판례 원문이 없어서 검색해봐야
    # "유류분" 등 비슷한 단어가 들어간 상품 안내 문구만 걸림 — MCP 실제 판례를 우선하고
    # 내부 검색은 스킵. 신탁 상품/법령 질의는 기존대로 내부 문서를 계속 사용.
    tokens, chunks = stream_answer(
        db,
        req.message,
        query_embedding,
        external_sources=external_sources,
        skip_internal=precedent_only,
    )

    stream = event_stream(
        db, session_id, tokens, chunks, external_sources, emit_sources=True, mcp_meta=mcp_meta
    )
    return StreamingResponse(stream, media_type="text/event-stream")


@router.post("/continue")
def chat_continue(req: ContinueRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """"더 설명해드릴까요?"에 "네"로 답했을 때 이어쓰기 — 재검색 없이 원래 근거로 이어서 생성."""
    session_id, query, previous_answer, chunks, external_sources = load_context_for_continue(
        db, req.message_id
    )
    tokens = continue_answer(query, previous_answer, chunks, external_sources)
    stream = event_stream(
        db,
        session_id,
        tokens,
        chunks,
        external_sources,
        emit_sources=False,
        continue_count=req.continue_count,
    )
    return StreamingResponse(stream, media_type="text/event-stream")
