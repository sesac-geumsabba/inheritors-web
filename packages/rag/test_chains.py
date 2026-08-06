"""chains.py 스모크 테스트: python packages/rag/test_chains.py
_strip_confidence_score는 DB/LLM 불필요. skip_internal 테스트만 DB 필요(LLM 호출은 없음 —
no-context 경로라 Ollama까지는 안 탐)."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
load_dotenv(Path(__file__).resolve().parents[2] / "apps" / "api" / ".env")

from packages.rag.chains import NO_CONTEXT_MESSAGE, _strip_confidence_score, stream_answer
from packages.rag.embeddings import embed_query


def joined(tokens: list[str]) -> str:
    return "".join(_strip_confidence_score(iter(tokens)))


def main() -> None:
    cases = [
        # 끝에 붙는 경우
        (["안녕", "하세요", ". 답변", "입니다", ".", "신뢰도", ": 9", "0%"], "안녕하세요. 답변입니다."),
        (["결과는", " 이렇습니다", ".", " [신뢰도", ": 80%]"], "결과는 이렇습니다."),
        # 맨 앞에 붙는 경우 (실측에서 발견)
        (["신뢰도", ": 90%", "유언대용신탁", " 계약에", " 따르면", "..."], "유언대용신탁 계약에 따르면..."),
        # 문장 중간의 "confidence: NN%"는 시작/끝 앵커에 안 걸리므로 보존 (오탐 방지)
        (["이 답변은 ", "confidence", ": 95", "%", "로 표시된", " 예시", "입니다."], "이 답변은 confidence: 95%로 표시된 예시입니다."),
        # 아무 패턴도 없는 정상 케이스
        (["평범한", " 답변", "이고", " 끝에", " 아무것도", " 없습니다", "."], "평범한 답변이고 끝에 아무것도 없습니다."),
    ]
    for tokens, expected in cases:
        result = joined(tokens)
        assert result == expected, f"기대: {expected!r}, 실제: {result!r}"
        print(f"[OK] {expected!r}")

    print("[PASS] confidence score strip (leading + trailing)")


def test_skip_internal() -> None:
    """skip_internal=True면 내부 문서가 실제로 관련 있어도 무시하고, 외부 소스도 없으면
    NO_CONTEXT_MESSAGE로 빠져야 함 (판례 질의가 신탁 상품설명서를 오답 근거로 안 쓰는지 확인)."""
    engine = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=engine)()

    # "신탁" 관련 질의라 내부 DB엔 top-1 스코어 0.6대 청크가 실제로 있음 (test_retriever.py 참고)
    embedding = embed_query("신탁 가입하면 수수료는 어떻게 되나요?")
    tokens, chunks = stream_answer(db, "신탁 판례를 알려주세요", embedding, skip_internal=True)
    db.close()

    assert chunks == [], f"skip_internal인데 내부 청크가 반환됨: {chunks}"
    answer = "".join(tokens)
    assert answer == NO_CONTEXT_MESSAGE, f"외부 소스 없이 skip_internal이면 no-context여야 함: {answer!r}"
    print("[PASS] skip_internal bypasses internal search")


if __name__ == "__main__":
    main()
    test_skip_internal()
