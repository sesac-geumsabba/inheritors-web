"""chunks.embedding에 대한 pgvector 코사인 유사도 검색. 기존 HNSW 인덱스(idx_chunks_embedding)를 그대로 탄다."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

DEFAULT_TOP_K = 5

_SEARCH_SQL = text("""
    SELECT c.id, c.document_id, c.page, c.content, d.file_name, d.category, d.bank, d.contract_type,
           1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    ORDER BY c.embedding <=> CAST(:embedding AS vector)
    LIMIT :k
""")


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    content: str
    page: int | None
    file_name: str
    category: str
    bank: str | None
    contract_type: str | None
    score: float


def to_vector_literal(embedding: list[float]) -> str:
    """psycopg2엔 pgvector 어댑터가 없어 문자열로 캐스팅 SQL에 넘긴다 (CAST(:x AS vector))."""
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


def search_chunks(
    db: Session, query_embedding: list[float], top_k: int = DEFAULT_TOP_K
) -> list[RetrievedChunk]:
    embedding = to_vector_literal(query_embedding)
    rows = db.execute(_SEARCH_SQL, {"embedding": embedding, "k": top_k}).all()
    return [
        RetrievedChunk(
            chunk_id=row.id,
            document_id=row.document_id,
            content=row.content,
            page=row.page,
            file_name=row.file_name,
            category=row.category,
            bank=row.bank,
            contract_type=row.contract_type,
            score=row.score,
        )
        for row in rows
    ]
