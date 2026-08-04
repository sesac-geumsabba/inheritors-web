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
from packages.rag.retriever import search_chunks

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


if __name__ == "__main__":
    main()
