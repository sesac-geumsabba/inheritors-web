"""_strip_confidence_score 스모크 테스트. DB/LLM 불필요: python packages/rag/test_chains.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from packages.rag.chains import _strip_confidence_score


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


if __name__ == "__main__":
    main()
