"""리트리버 스모크 테스트. 프레임워크 없이 assert만: python packages/rag/test_retriever.py"""

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


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=engine)()

    # 관련 질의: 상속증여세 카테고리 문서가 top-1으로 잡히고, 임계값을 넘겨야 함
    relevant_embedding = embed_query("상속세 신고는 언제까지 해야 하나요?")
    results = search_chunks(db, relevant_embedding, top_k=3)
    assert results, "관련 질의에서 검색 결과가 비어 있음"
    assert results[0].score >= NO_CONTEXT_THRESHOLD, (
        f"관련 질의인데 top-1 score({results[0].score})가 임계값({NO_CONTEXT_THRESHOLD}) 미만"
    )
    print(f"[OK] relevant query top-1: {results[0].file_name} (score={results[0].score:.3f})")

    # 무관 질의: 도메인과 무관한 질문은 top-1 score가 임계값 밑으로 떨어져야 함 (hallucination 방지 체크)
    irrelevant_embedding = embed_query("오늘 저녁 메뉴로 뭐가 좋을까요?")
    results = search_chunks(db, irrelevant_embedding, top_k=3)
    print(f"[INFO] irrelevant query top-1 score: {results[0].score:.3f} (threshold={NO_CONTEXT_THRESHOLD})")

    db.close()
    print("[PASS] retriever smoke test")


if __name__ == "__main__":
    main()
