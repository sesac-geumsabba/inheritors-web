"""lexguard-mcp(SeoNaRu/lexguard-mcp) 판례 검색 폴백 클라이언트.

korean-law-mcp(mcp_client.py, chrisryugj)가 검색어/rate limit 문제로 0건을 반환할 때만
mcp_agent.select_and_run()이 이 클라이언트를 보조로 호출한다 — 서로 다른 국가법령정보센터
API 키(LAW_OC vs LAW_API_KEY)로 동작하는 별개 서버라 한쪽이 막혀도 다른 쪽에서 잡힐 수 있다.

korean-law-mcp는 stdio(자식 프로세스)지만 lexguard-mcp는 Streamable HTTP(SSE)로 통신한다 —
프로토콜이 달라 mcp_client.py의 수기 JSON-RPC 코드를 재사용할 수 없어 공식 `mcp` SDK를 쓴다.
호출 빈도가 낮은 폴백이라(주 경로가 대부분 처리) 프로세스처럼 상주시키지 않고 매 호출마다
세션을 새로 연다 — korean-law-mcp급 최적화가 필요할 만큼 자주 불리지 않는다.
"""

import os
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class LexguardMCPClient:
    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("LEXGUARD_MCP_URL", "http://localhost:9099/mcp")

    async def _call_tool(
        self, tool_name: str, arguments: dict[str, Any], timeout: float = 5.0
    ) -> dict[str, Any]:
        try:
            async with streamable_http_client(self.url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        tool_name, arguments, read_timeout_seconds=timeout
                    )
            # mcp SDK 응답 모델은 MCP 스펙상 camelCase(isError/structuredContent)를 pydantic
            # alias로만 받고, 파이썬 쪽 실제 속성명은 snake_case다(is_error/structured_content —
            # 실제 서버에 더미 키로 호출해 실측 확인, 문서/타입 힌트만 보고 짐작하면 틀림).
            if result.is_error:
                detail = "; ".join(getattr(c, "text", "") for c in result.content)
                return {"error": detail or f"lexguard-mcp {tool_name} 호출 실패"}
            # outputSchema가 있는 tool이라 structured_content에 파싱된 dict가 그대로 온다
            # (content는 사람이 읽는 text 표현이라 별도 파싱이 더 필요해서 우선순위 낮음).
            return result.structured_content or {}
        except Exception as e:
            return {"error": str(e)}

    async def search_decisions(self, query: str, timeout: float = 5.0) -> list[dict]:
        """판례 검색. korean-law-mcp가 0건일 때만 mcp_agent.py가 이 메서드를 호출한다.

        precedent_lookup_tool 응답의 precedents 항목은 영문 별칭(case_name 등)과 법제처
        원본 한글 키(사건명 등)가 소스에 따라 섞여 있어(lexguard-mcp의
        src/routes/resource_handlers.py 실측 확인) 둘 다 방어적으로 조회한다.
        """
        resp = await self._call_tool("precedent_lookup_tool", {"keyword": query}, timeout=timeout)
        if resp.get("error"):
            return []

        items = resp.get("precedents") or []
        sources: list[dict] = []
        for i, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            case_name = item.get("case_name") or item.get("사건명", "")
            case_number = item.get("case_number") or item.get("사건번호", "")
            court = item.get("court_name") or item.get("법원명", "")
            date = item.get("judgment_date") or item.get("선고일자", "")
            summary = (
                item.get("summary")
                or item.get("판시사항")
                or item.get("판결요지")
                or f"{case_name} {case_number}".strip()
            )
            title_bits = [b for b in (case_name or case_number, court, date) if b]
            sources.append(
                {
                    "source_type": "case_law",
                    "title": f"판례 검색(lexguard): {' '.join(title_bits) or query}",
                    "url": "https://glaw.scourt.go.kr",
                    "snippet": (summary or "")[:500],
                    "score": round(1.0 - (i * 0.1), 2),
                    "rank": i,
                }
            )
        return sources


# mcp_agent.py가 공유해서 쓰는 단일 인스턴스 — korean-law-mcp의 mcp_client와 달리 상주
# 프로세스가 없어 FastAPI lifespan에 start()/aclose()를 걸 필요는 없다.
lexguard_client = LexguardMCPClient()
