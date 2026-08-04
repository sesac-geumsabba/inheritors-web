from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.chat import ChatRequest
from app.db import get_db
from packages.rag.chains import stream_answer
from packages.rag.embeddings import embed_query
from packages.rag.retriever import RetrievedChunk, to_vector_literal

router = APIRouter(prefix="/chat", tags=["Chat"])


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


def _save_sources(db: Session, message_id: int, chunks: list[RetrievedChunk]) -> None:
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


@router.post("")
def chat(req: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    session_id = req.session_id or _create_session(db)
    query_embedding = embed_query(req.message)
    _save_message(db, session_id, "user", req.message, query_embedding)

    tokens, chunks = stream_answer(db, req.message, query_embedding)

    def event_stream() -> Iterator[str]:
        parts: list[str] = []
        for token in tokens:
            parts.append(token)
            # SSE는 data 라인 안에 개행이 오면 각 줄마다 "data: "를 다시 붙여야 한다.
            yield "data: " + token.replace("\n", "\ndata: ") + "\n\n"

        message_id = _save_message(db, session_id, "assistant", "".join(parts), None)
        _save_sources(db, message_id, chunks)
        yield f"event: done\ndata: {{\"session_id\": {session_id}}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
