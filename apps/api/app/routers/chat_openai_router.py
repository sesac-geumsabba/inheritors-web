"""신규 OpenAI(GPT) 기반 챗봇 — /chat 프론트(상담소, 프로덕션)가 호출한다.

검색/MCP/DB 저장/SSE 스트리밍 로직은 app/chat_shared.py를 chat_router.py와 그대로 공유하고,
LLM 호출부만 packages.rag.openai_chains(ChatOpenAI)를 쓴다. 기존 Ollama 버전은
routers/chat_router.py(/prototype/chat 프론트용)로 그대로 남아있다.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.chat import ChatRequest, ContinueRequest
from app.chat_shared import (
    create_session,
    event_stream,
    fetch_external_sources,
    is_precedent_only,
    load_context_for_continue,
    save_message,
)
from app.db import get_db
from packages.rag.embeddings import embed_query
from packages.rag.openai_chains import continue_answer, stream_answer

router = APIRouter(prefix="/chat/openai", tags=["Chat (OpenAI)"])


@router.post("")
async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    session_id = req.session_id or create_session(db)
    query_embedding = embed_query(req.message)
    save_message(db, session_id, "user", req.message, query_embedding)

    external_sources = await fetch_external_sources(req.message)
    tokens, chunks = stream_answer(
        db,
        req.message,
        query_embedding,
        external_sources=external_sources,
        skip_internal=is_precedent_only(req.message),
    )

    stream = event_stream(db, session_id, tokens, chunks, external_sources, emit_sources=True)
    return StreamingResponse(stream, media_type="text/event-stream")


@router.post("/continue")
def chat_continue(req: ContinueRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """"더 설명해드릴까요?"에 "네"로 답했을 때 이어쓰기 — 재검색 없이 원래 근거로 이어서 생성."""
    session_id, query, previous_answer, chunks, external_sources = load_context_for_continue(
        db, req.message_id
    )
    tokens = continue_answer(query, previous_answer, chunks, external_sources)
    stream = event_stream(db, session_id, tokens, chunks, external_sources, emit_sources=False)
    return StreamingResponse(stream, media_type="text/event-stream")
