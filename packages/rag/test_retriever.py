"""리트리버 스모크 테스트. 프레임워크 없이 assert만: python packages/rag/test_retriever.py

카테고리별(설명서/계약서/상속증여세) 관련 질의 + 경계(금융이지만 무관)/완전무관 질의로
NO_CONTEXT_THRESHOLD 분리가 여전히 유효한지 회귀 체크.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
load_dotenv(Path(__file__).resolve().parents[2] / "apps" / "api" / ".env")

from packages.rag.chains import NO_CONTEXT_THRESHOLD
from packages.rag.embeddings import embed_query
from packages.rag.retriever import (
    detect_bank,
    detect_contract_type,
    search_chunks,
    search_chunks_balanced,
)

RELATED_CASES = [
    "IBK 유언대용신탁 상품의 주요 특징이 뭐야?",
    "신탁 가입하면 수수료는 어떻게 되나요?",
    "수익자를 변경하려면 어떤 절차가 필요해?",
    "위탁자가 사망하면 신탁재산은 어떻게 처리돼?",
    "상속세 신고 기한이 언제까지야?",
    "증여세 면제 한도가 얼마나 돼?",
]
UNRELATED_CASES = [
    "주식 투자는 어떻게 시작하나요?",  # 경계: 금융이지만 신탁과 무관
    "적금 이자율이 높은 은행 추천해줘",  # 경계
    "오늘 저녁 메뉴로 뭐가 좋을까요?",  # 완전 무관
    "파이썬으로 웹크롤러 어떻게 만들어?",  # 완전 무관
]


def top1_score(db, query: str) -> float:
    embedding = embed_query(query)
    return search_chunks(db, embedding, top_k=1)[0].score


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=engine)()

    related_scores = [top1_score(db, q) for q in RELATED_CASES]
    unrelated_scores = [top1_score(db, q) for q in UNRELATED_CASES]
    db.close()

    print(f"관련 질의 top-1 최소: {min(related_scores):.3f}")
    print(f"무관/경계 질의 top-1 최대: {max(unrelated_scores):.3f}")
    print(f"임계값: {NO_CONTEXT_THRESHOLD}")

    assert min(related_scores) > NO_CONTEXT_THRESHOLD, (
        "관련 질의 중 임계값 아래로 떨어지는 게 있음 — 정상 질문이 '자료 없음'으로 오답될 위험"
    )
    assert max(unrelated_scores) < NO_CONTEXT_THRESHOLD, (
        "무관/경계 질의 중 임계값을 넘는 게 있음 — 관련 없는 내용에 LLM이 답변을 지어낼(hallucination) 위험"
    )

    print("[PASS] retriever threshold separation")


def test_detect_metadata() -> None:
    assert detect_bank("하나은행 계약서에서는 어떻게 되나요?") == "하나은행"
    assert detect_bank("국민은행 상품이 궁금해요") == "KB국민은행"
    assert detect_bank("기업은행에서 가입 가능한가요?") == "IBK기업은행"
    assert detect_bank("신탁 수수료가 궁금해요") is None
    assert detect_contract_type("부동산관리신탁 계약 내용 알려줘") == "부동산관리신탁"
    assert detect_contract_type("일반적인 신탁 질문입니다") is None
    print("[PASS] detect_bank / detect_contract_type")


def test_category_balanced() -> None:
    """카테고리별 top-k를 따로 조회해 합치므로, 특정 카테고리가 결과를 독식하지 않아야 함."""
    engine = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=engine)()

    embedding = embed_query("유언대용신탁 관련해서 전반적으로 알려주세요")
    results = search_chunks_balanced(db, embedding, per_category_k=3)
    categories_hit = {c.category for c in results}
    db.close()

    assert len(results) <= 9, f"카테고리 3개 x k=3인데 {len(results)}건 나옴"
    assert len(categories_hit) >= 2, f"카테고리 다양성이 없음: {categories_hit}"
    print(f"[PASS] category-balanced retrieval (categories hit: {categories_hit})")


def test_bank_filter() -> None:
    """은행명이 감지되면 계약서 카테고리 결과가 전부 그 은행 문서로만 좁혀져야 함."""
    engine = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=engine)()

    embedding = embed_query("하나은행 계약서에서는 중도해지 시 어떻게 되나요?")
    results = search_chunks_balanced(db, embedding, per_category_k=3, bank="하나은행")
    contract_results = [c for c in results if c.category == "계약서"]
    db.close()

    assert contract_results, "하나은행 계약서 카테고리 결과가 아예 없음"
    assert all(c.bank == "하나은행" for c in contract_results), (
        f"bank 필터를 걸었는데 다른 은행 문서가 섞임: {[c.bank for c in contract_results]}"
    )
    print("[PASS] bank-filtered contract search")


if __name__ == "__main__":
    main()
    test_detect_metadata()
    test_category_balanced()
    test_bank_filter()
