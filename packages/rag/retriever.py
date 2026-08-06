"""chunks.embedding에 대한 pgvector 코사인 유사도 검색. 기존 HNSW 인덱스(idx_chunks_embedding)를 그대로 탄다."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

DEFAULT_TOP_K = 5
PER_CATEGORY_TOP_K = 3
CATEGORIES = ["설명서", "상속증여세", "계약서"]


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


def _row_to_chunk(row) -> RetrievedChunk:
    return RetrievedChunk(
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


def search_chunks(
    db: Session,
    query_embedding: list[float],
    top_k: int = DEFAULT_TOP_K,
    category: str | None = None,
    bank: str | None = None,
    contract_type: str | None = None,
) -> list[RetrievedChunk]:
    """단일 검색. category/bank/contract_type을 주면 해당 조건 + 벡터 유사도로 필터링.

    조건절은 고정된 컬럼 화이트리스트(category/bank/contract_type)로만 구성되고 실제 값은
    전부 바인드 파라미터로 넘어가서, SQL 인젝션 위험 없이 동적 WHERE절을 구성한다.
    """
    embedding = to_vector_literal(query_embedding)
    conditions = []
    params: dict = {"embedding": embedding, "k": top_k}
    if category is not None:
        conditions.append("d.category = :category")
        params["category"] = category
    if bank is not None:
        conditions.append("d.bank = :bank")
        params["bank"] = bank
    if contract_type is not None:
        conditions.append("d.contract_type = :contract_type")
        params["contract_type"] = contract_type
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = text(f"""
        SELECT c.id, c.document_id, c.page, c.content, d.file_name, d.category, d.bank, d.contract_type,
               1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        {where_clause}
        ORDER BY c.embedding <=> CAST(:embedding AS vector)
        LIMIT :k
    """)
    rows = db.execute(sql, params).all()
    return [_row_to_chunk(row) for row in rows]


def search_chunks_balanced(
    db: Session,
    query_embedding: list[float],
    per_category_k: int = PER_CATEGORY_TOP_K,
    bank: str | None = None,
    contract_type: str | None = None,
) -> list[RetrievedChunk]:
    """카테고리(설명서/상속증여세/계약서)별로 top-k를 따로 조회해 합친다 — 단일 전역 top-k면
    질의와 가장 가까운 카테고리 하나가 결과를 독식해서 다른 성격의 근거가 밀려날 수 있음.

    bank/contract_type 필터는 해당 컬럼이 있는 문서에만 의미가 있음(설명서엔 bank만 존재,
    상속증여세엔 둘 다 없음) — 없는 카테고리에 필터를 걸면 자연히 0건이 되어 안전하게 무시된다.
    contract_type은 계약서 카테고리에만 적용 (다른 카테고리는 항상 NULL이라 걸면 전멸함).
    """
    results: list[RetrievedChunk] = []
    for category in CATEGORIES:
        results.extend(
            search_chunks(
                db,
                query_embedding,
                top_k=per_category_k,
                category=category,
                bank=bank,
                contract_type=contract_type if category == "계약서" else None,
            )
        )
    results.sort(key=lambda c: c.score, reverse=True)
    return results


# ponytail: 은행명/신탁유형은 문서 메타데이터 그대로의 축약형 매핑. 새 은행/유형이 추가되면
# 여기 사전에 추가해야 함 — 완전한 NER은 아니고 이 코퍼스(documents.bank/contract_type
# distinct 값 6종/2종) 기준 curated 목록.
# "KB"/"IBK"는 실사용 중 "KB 계약서 보여줘"처럼 "은행" 없이 줄여 부르는 질의에서 감지가
# 안 돼(설명서/계약서 카테고리 필터가 안 걸려) 다른 은행 문서가 섞여 나온 문제(실측 확인)라
# 추가함. "우리"/"하나"/"신한"/"기업"은 같은 이유로 bare alias를 추가하고 싶지만 각각
# "우리 아버지", "이 중 하나", "기업 상속세" 등 일반 단어와 겹쳐 오탐(엉뚱한 은행으로 필터링)
# 위험이 커서 뺐다 — "OO은행" 형태 풀네임으로만 잡는다.
_BANK_ALIASES: dict[str, str] = {
    "KB국민은행": "KB국민은행",
    "국민은행": "KB국민은행",
    "KB": "KB국민은행",
    "IBK기업은행": "IBK기업은행",
    "기업은행": "IBK기업은행",
    "IBK": "IBK기업은행",
    "우리은행": "우리은행",
    "신한은행": "신한은행",
    "하나은행": "하나은행",
}
_CONTRACT_TYPE_ALIASES: dict[str, str] = {
    "유언대용신탁": "유언대용신탁",
    "부동산관리신탁": "부동산관리신탁",
}


def detect_bank(query: str) -> str | None:
    return next((canonical for alias, canonical in _BANK_ALIASES.items() if alias in query), None)


def detect_contract_type(query: str) -> str | None:
    return next(
        (canonical for alias, canonical in _CONTRACT_TYPE_ALIASES.items() if alias in query), None
    )
