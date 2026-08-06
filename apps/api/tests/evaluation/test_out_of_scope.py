"""RAG 범위 밖 질문(out-of-scope) 평가 스크립트.

docs/RAG_OUT_OF_SCOPE_EVALUATION.md의 지시에 따라 실제 챗봇 파이프라인(/chat/openai)을
호출해 관련 없는 질문 20개에 대한 라우팅/RAG 근거 사용/MCP 호출/citation/최종 답변을 평가한다.

실행: python apps/api/tests/evaluation/test_out_of_scope.py  (apps/api가 cwd 기준 import root)

이 스크립트는 실제 OpenAI API를 호출한다(질문당 최대 2회: MCP tool-calling LLM + 최종 답변
생성 LLM). 외부 korean-law-mcp 프로세스 호출만 mock으로 대체해 비용/불안정성을 피하되,
mock의 호출 횟수는 그대로 기록해 "MCP를 실제로 호출하려 했는지"를 검증할 수 있게 한다
(docs/RAG_OUT_OF_SCOPE_EVALUATION.md 2.3절 요구사항).

프로덕션 라우팅 로직/프롬프트는 이 스크립트에서 전혀 수정하지 않는다 — 관찰만 한다.
"""

import json
import re
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

API_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(API_ROOT))

from dotenv import load_dotenv

load_dotenv(API_ROOT / ".env")

from fastapi.testclient import TestClient

from app.main import app
from app.mcp_client import mcp_client

QUERIES_PATH = Path(__file__).resolve().parent / "out_of_scope_queries.json"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
RESULTS_JSON_PATH = RESULTS_DIR / "out_of_scope_results.json"
SUMMARY_MD_PATH = RESULTS_DIR / "out_of_scope_summary.md"

# 확인용 — 이름만 확인하고 값은 절대 출력하지 않는다 (RAG_OUT_OF_SCOPE_EVALUATION.md 9.1절).
_REQUIRED_ENV_NAMES = ["OPENAI_API_KEY", "OPENAI_MODEL", "MCP_AGENT_MODEL", "DATABASE_URL"]

# NO_CONTEXT_MESSAGE(packages/rag/chains.py)와, LLM이 SYSTEM_PROMPT 지침에 따라 스스로
# 생성할 수 있는 "범위를 벗어난다"류 표현을 함께 감지하는 키워드 휴리스틱이다. 실제 의미
# 판단(semantic judgment)이 아니라 문자열 매칭이므로, PASS/FAIL 결과는 요약 보고서 작성
# 시 answer 원문을 사람이 다시 한번 훑어보는 방식으로 보정한다.
_SCOPE_GUIDANCE_MARKERS = (
    "범위를 벗어",
    "답변 범위",
    "지원하지 않는",
    "지원 범위",
    "관련된 자료를 찾지 못했",
    "PB 상담",
    "다른 표현으로 다시 질문",
)


def looks_like_scope_guidance(answer: str) -> bool:
    return any(marker in answer for marker in _SCOPE_GUIDANCE_MARKERS)


def parse_sse(body_text: str) -> dict:
    """SSE 응답 본문을 event 타입별로 파싱. 프론트(chat/page.tsx)의 consumeStream과 동일한 규칙."""
    sources: list[dict] = []
    mcp_status: dict | None = None
    answer_parts: list[str] = []

    for block in body_text.split("\n\n"):
        if not block.strip():
            continue
        event_type = "message"
        data_lines = []
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[len("event: "):]
            elif line.startswith("data: "):
                data_lines.append(line[len("data: "):])
        data = "\n".join(data_lines)
        if not data:
            continue

        if event_type == "sources":
            sources = json.loads(data)
        elif event_type == "mcp_status":
            mcp_status = json.loads(data)
        elif event_type in ("awaiting_continue", "done"):
            continue
        else:
            answer_parts.append(data)

    return {
        "sources": sources,
        "mcp_status": mcp_status or {"called": False, "tools": [], "reason": ""},
        "answer": "".join(answer_parts),
    }


def run_one(client: TestClient, query: str, search_law_mock: AsyncMock, search_decisions_mock: AsyncMock) -> dict:
    calls_before = search_law_mock.await_count + search_decisions_mock.await_count

    t0 = time.monotonic()
    error: str | None = None
    parsed = {"sources": [], "mcp_status": {"called": False, "tools": [], "reason": ""}, "answer": ""}
    try:
        with client.stream("POST", "/chat/openai", json={"message": query}, timeout=120.0) as response:
            body_text = "".join(response.iter_text())
        parsed = parse_sse(body_text)
    except Exception as e:  # noqa: BLE001 — 평가 스크립트: 한 문항 실패해도 나머지는 계속 진행
        error = f"{type(e).__name__}: {e}"
    latency_ms = round((time.monotonic() - t0) * 1000, 1)

    calls_after = search_law_mock.await_count + search_decisions_mock.await_count
    mcp_call_count = calls_after - calls_before

    sources = parsed["sources"]
    internal_sources = [s for s in sources if s.get("source_type") == "internal_chunk"]
    external_sources = [s for s in sources if s.get("source_type") != "internal_chunk"]
    mcp_status = parsed["mcp_status"]
    answer = parsed["answer"]

    rag_evidence_used = len(internal_sources) > 0
    mcp_called = bool(mcp_status.get("called"))

    # rag_search_called: API가 "내부 검색을 실제로 실행했는지" 자체를 노출하지 않는다.
    # skip_internal(=precedent_only)일 때만 내부 검색이 생략되는데, precedent_only는
    # SSE로 직접 오지 않아 mcp_status.tools + case_law 소스 존재 여부로만 "추정"할 수 있다
    # — 아래 값은 관찰이 아니라 추론이며, 요약 보고서의 "관찰할 수 없었던 항목"에 명시한다.
    has_case_law = any(s.get("source_type") == "case_law" for s in sources)
    precedent_only_inferred = (
        "search_decisions" in mcp_status.get("tools", [])
        and "search_law" not in mcp_status.get("tools", [])
        and has_case_law
    )
    rag_search_called_inferred = not precedent_only_inferred

    citations = [s.get("title", "") for s in sources]

    scope_guidance_ok = looks_like_scope_guidance(answer) if not error else False
    # route는 API가 반환하는 필드가 아니다(코드 어디에도 "out_of_scope" 라벨이 없음) — 아래는
    # 순수히 평가용으로 파생시킨 라벨이다. 상세 근거는 요약 보고서에 기록.
    actual_route_inferred = (
        "out_of_scope"
        if (not rag_evidence_used and not mcp_called and scope_guidance_ok)
        else "in_scope"
    )

    checks = {
        "route": actual_route_inferred == "out_of_scope",
        "rag_evidence": not rag_evidence_used,
        "mcp": not mcp_called,
        "citations": len(citations) == 0,
        "scope_guidance": scope_guidance_ok,
    }
    score = sum(1 for v in checks.values() if v) if not error else 0
    result = "ERROR" if error else ("PASS" if score == 5 else "FAIL")
    failure_reason = None
    if error:
        failure_reason = error
    elif result == "FAIL":
        failure_reason = ", ".join(k for k, v in checks.items() if not v)

    return {
        "actual_route": actual_route_inferred,
        "route_basis": "inferred (no native route field in API)",
        "rag_search_called": rag_search_called_inferred,
        "rag_search_called_basis": "inferred from mcp_status + case_law source presence, not directly observed",
        "rag_evidence_used": rag_evidence_used,
        "retrieved_documents": [s.get("title") for s in internal_sources],
        "similarity_scores": [s.get("score") for s in internal_sources],
        "mcp_called": mcp_called,
        "mcp_call_count": mcp_call_count,
        "mcp_tools": mcp_status.get("tools", []),
        "citations": citations,
        "answer": answer,
        "latency_ms": latency_ms,
        "checks": checks,
        "score": score,
        "result": result,
        "failure_reason": failure_reason,
        "error": error,
    }


def main() -> None:
    import os

    print("환경변수 확인 (이름만, 값은 출력하지 않음):")
    missing = []
    for name in _REQUIRED_ENV_NAMES:
        present = bool(os.environ.get(name))
        print(f"  {name}: {'SET' if present else 'MISSING'}")
        if not present:
            missing.append(name)
    if missing:
        print(f"[FATAL] 필수 환경변수 누락: {missing}. 평가를 중단합니다.")
        sys.exit(1)

    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    assert len(queries) == 20, f"질문이 20개가 아님: {len(queries)}"

    results = []
    with (
        patch.object(mcp_client, "search_law", new=AsyncMock(return_value=[])) as search_law_mock,
        patch.object(mcp_client, "search_decisions", new=AsyncMock(return_value=[])) as search_decisions_mock,
        TestClient(app) as client,
    ):
        for item in queries:
            print(f"[{item['id']:2d}/20] ({item['category']}) {item['query']}")
            outcome = run_one(client, item["query"], search_law_mock, search_decisions_mock)
            row = {
                "id": item["id"],
                "category": item["category"],
                "query": item["query"],
                "expected_route": "out_of_scope",
                **outcome,
            }
            results.append(row)
            print(f"         -> {row['result']} (score={row['score']}/5, latency={row['latency_ms']}ms)")
            if row["failure_reason"]:
                print(f"         reason: {row['failure_reason']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    assert len(results) == 20, f"결과가 20개가 아님: {len(results)}"

    total_score = sum(r["score"] for r in results)
    pass_count = sum(1 for r in results if r["result"] == "PASS")
    error_count = sum(1 for r in results if r["result"] == "ERROR")
    out_of_scope_correct = sum(1 for r in results if r["actual_route"] == "out_of_scope")
    mcp_called_count = sum(1 for r in results if r["mcp_called"])
    bad_rag_count = sum(1 for r in results if r["rag_evidence_used"])
    bad_citation_count = sum(1 for r in results if len(r["citations"]) > 0)
    direct_answer_count = sum(1 for r in results if not r["checks"]["scope_guidance"] and not r["error"])

    n = len(results)
    metrics = {
        "block_rate_pct": round(out_of_scope_correct / n * 100, 1),
        "unnecessary_mcp_call_rate_pct": round(mcp_called_count / n * 100, 1),
        "wrong_rag_evidence_rate_pct": round(bad_rag_count / n * 100, 1),
        "wrong_citation_rate_pct": round(bad_citation_count / n * 100, 1),
        "direct_answer_rate_pct": round(direct_answer_count / n * 100, 1),
    }

    by_category: dict[str, list[dict]] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    category_labels = {
        "daily_life": "일상 질문",
        "it_science": "IT·과학·학습 질문",
        "general_finance": "일반 금융 질문",
        "keyword_trap": "키워드 함정 질문",
    }

    lines = []
    lines.append("# Out-of-Scope Evaluation Result")
    lines.append("")
    lines.append("## 실행 환경")
    lines.append(f"- 실행 일시: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("- 테스트 대상 엔드포인트: POST /chat/openai (apps/api/app/routers/chat_openai_router.py)")
    lines.append("- 테스트 실행 명령어: `python apps/api/tests/evaluation/test_out_of_scope.py` (cwd: apps/api)")
    lines.append("- 총 문항 수: 20")
    lines.append("")
    lines.append("## 전체 결과")
    lines.append(f"- 총점: {total_score}/100")
    lines.append(f"- PASS 문항 수: {pass_count}/20 (ERROR {error_count}건 포함 여부와 별개로 집계)")
    lines.append(f"- 범위 밖 질문 차단율: {metrics['block_rate_pct']}%")
    lines.append(f"- 불필요한 MCP 호출률: {metrics['unnecessary_mcp_call_rate_pct']}%")
    lines.append(f"- 잘못된 근거 사용률: {metrics['wrong_rag_evidence_rate_pct']}%")
    lines.append(f"- 잘못된 Citation 비율: {metrics['wrong_citation_rate_pct']}%")
    lines.append(f"- 범위 밖 직접 답변률: {metrics['direct_answer_rate_pct']}%")
    lines.append("")
    lines.append("## 유형별 결과")
    for cat_key, label in category_labels.items():
        rows = by_category.get(cat_key, [])
        cat_pass = sum(1 for r in rows if r["result"] == "PASS")
        cat_score = sum(r["score"] for r in rows)
        lines.append(f"- {label}: PASS {cat_pass}/{len(rows)}, 점수 {cat_score}/{len(rows) * 5}")
    lines.append("")
    lines.append("## 실패 사례")
    lines.append("| ID | 질문 | 실제 동작 | 실패 항목 | 추정 원인 |")
    lines.append("|---:|---|---|---|---|")
    for r in results:
        if r["result"] == "PASS":
            continue
        actual = (
            f"route={r['actual_route']}, rag_used={r['rag_evidence_used']}, "
            f"mcp_called={r['mcp_called']}, citations={len(r['citations'])}건"
        )
        answer_preview = re.sub(r"\s+", " ", r["answer"])[:80]
        reason = r["failure_reason"] or "-"
        lines.append(
            f"| {r['id']} | {r['query']} | {actual} / 답변: \"{answer_preview}...\" | {reason} | (아래 개선 제안 참고) |"
        )
    lines.append("")
    lines.append("## 관찰할 수 없었던 항목")
    lines.append(
        "- `actual_route`: API가 명시적인 route/out_of_scope 필드를 반환하지 않는다. "
        "본 스크립트는 `rag_evidence_used=False`, `mcp_called=False`, 답변이 범위 안내 문구를 "
        "포함하는지(키워드 휴리스틱)를 조합해 **추론**했다 — 실제 시스템이 내린 판단이 아니라 "
        "평가를 위해 사후에 파생시킨 라벨이다."
    )
    lines.append(
        "- `rag_search_called`: 내부 벡터 검색이 실제로 실행됐는지 자체를 API가 노출하지 않는다. "
        "`mcp_status.tools`와 `case_law` 소스 존재 여부로 `skip_internal`(precedent_only) 여부를 "
        "역으로 추정했을 뿐, 직접 관찰한 값이 아니다."
    )
    lines.append(
        "- `similarity_scores`(거부된 후보 청크): `chains.py`의 `stream_answer()`는 임계값을 "
        "통과하지 못한 청크는 `used_chunks`에 포함하지 않아 SSE `sources` 이벤트에도 나타나지 "
        "않는다. 즉 \"검색은 됐지만 버려진\" 청크의 실제 top-1 유사도 점수는 현재 API로는 "
        "NOT_OBSERVABLE — `chat_shared.py`나 `chains.py`에 진단용 로그(예: 내부 검색 top-1 "
        "score를 stderr에 남기는 정도)를 추가하면 관찰 가능해진다(동작에는 영향 없음)."
    )
    lines.append(
        "- `scope_guidance` 판정: 실제 의미 판단이 아니라 고정 키워드 매칭이다. LLM이 다른 "
        "표현으로 범위를 안내했다면 오탐(실패로 잘못 분류)될 수 있고, 반대로 범위 안내 문구를 "
        "섞어 쓰면서 일반 지식 답변도 같이 준 경우(문서 4항 마지막 유의사항)는 이 휴리스틱으로 "
        "구분하지 못한다 — 아래 실패 사례의 답변 원문(`out_of_scope_results.json`)을 사람이 "
        "직접 확인하는 걸 권장한다."
    )
    lines.append("")
    lines.append("## 개선 제안")
    lines.append("(실제 실패 로그 확인 후 아래 표를 근거로 구체화 — 스크립트가 자동으로 채우지 않음)")
    lines.append("")

    SUMMARY_MD_PATH.write_text("\n".join(lines), encoding="utf-8")

    print()
    print(f"결과 JSON: {RESULTS_JSON_PATH}")
    print(f"요약 리포트: {SUMMARY_MD_PATH}")
    print(f"총점: {total_score}/100, PASS {pass_count}/20, ERROR {error_count}건")
    print(f"지표: {metrics}")


if __name__ == "__main__":
    main()
