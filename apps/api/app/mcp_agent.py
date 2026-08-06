"""LLM 기반 MCP(korean-law-mcp) tool-calling — 고정 키워드/정규식 라우팅을 대체.

chat_shared.py의 fetch_external_sources()가 이 모듈의 select_and_run()을 호출한다.
MCP 호출 여부, search_law/search_decisions 중 어떤 도구를 쓸지, 각 도구에 전달할 검색어
모두 OpenAI tool-calling LLM이 질문의 의미를 보고 직접 판단한다 (docs/NEW_MCP.md 참고).
"""

import asyncio
import os
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.lexguard_client import lexguard_client
from app.mcp_client import mcp_client

SYSTEM_PROMPT = """당신은 신탁, 상속, 증여 분야의 법률 검색 도구 선택 에이전트다.

사용자 질문을 이해하고, 정확한 답변을 위해 외부 법령 또는 판례 검색이
필요한 경우에만 제공된 도구를 호출하라.

- 현행 법령이나 법적 개념, 요건, 절차, 권리 확인이 필요하면
  search_law_tool을 호출한다.
- 실제 법원의 판단, 대법원 판례, 사건 사례 또는 판결 동향이 필요하면
  search_decisions_tool을 호출한다.
- 법령과 판례가 모두 필요하면 두 도구를 모두 호출할 수 있다.
- 신탁, 상속, 증여와 관련이 없거나 외부 법률 근거가 필요하지 않은
  질문이면 아무 도구도 호출하지 않는다.
- 사용자가 정확한 법률 용어를 사용하지 않았더라도 질문의 의미를
  분석하여 관련 법적 쟁점을 판단한다.
- 검색어는 자연어 문장이 아니라 1~3개의 핵심 법률 용어로 작성한다.
- 검색 엔진은 공백으로 구분된 단어를 모두 포함하는 문서만 찾으므로
  불필요한 단어를 넣지 않는다.
- 질문에 없는 법률명, 사건번호 또는 판결 내용을 임의로 만들어내지 않는다.
- 사용자가 법령만 또는 판례만 요청했다면 해당 요청 범위를 우선한다.
"""

_MAX_QUERY_LEN = 100


@tool
async def search_law_tool(query: str) -> list[dict]:
    """신탁, 상속, 증여와 관련된 대한민국 법령을 검색한다.

    검색 엔진은 공백으로 구분된 단어를 AND 조건으로 처리한다.
    사용자의 자연어 질문 전체를 전달하지 말고, 법적 쟁점을 나타내는
    1~3개의 핵심 법률 용어만 query에 전달한다.

    실제 판례나 법원의 판단을 찾을 때는 이 도구가 아니라
    search_decisions_tool을 사용한다.
    """
    return await mcp_client.search_law(query)


@tool
async def search_decisions_tool(query: str) -> list[dict]:
    """신탁, 상속, 증여와 관련된 대한민국 판례를 검색한다.

    검색 엔진은 공백으로 구분된 단어를 AND 조건으로 처리한다.
    사용자의 자연어 질문 전체를 전달하지 말고, 판례의 법적 쟁점을
    나타내는 1~3개의 핵심 법률 용어만 query에 전달한다.

    일반적인 법령 조문이나 제도 설명만 필요하면
    search_law_tool을 사용한다.
    """
    return await mcp_client.search_decisions(query)


_TOOL_NAME_TO_MCP_NAME = {
    "search_law_tool": "search_law",
    "search_decisions_tool": "search_decisions",
}


@lru_cache(maxsize=1)
def _agent_llm():
    model = os.environ.get("MCP_AGENT_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(
        model=model,
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=0,
    ).bind_tools([search_law_tool, search_decisions_tool])


async def select_and_run(query: str) -> tuple[list[dict], set[str], list[dict]]:
    """질문을 분석해 MCP 도구 호출 여부/종류/검색어를 LLM이 판단하고 실행한다.

    실패 시 항상 빈 결과로 폴백한다 — MCP/LLM 오류가 전체 채팅 요청을 막지 않아야 한다.
    세 번째 반환값(tool_calls_used)은 실제로 mcp_client에 넘긴 (도구, 검색어) 목록으로,
    프론트에 "왜 MCP를 호출했는지"를 보여주는 용도로 chat_shared에서 사용한다.
    """
    try:
        response = await _agent_llm().ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=query),
            ]
        )
    except Exception as e:
        print(f"[error] mcp_agent tool-calling LLM 호출 실패: {e}")
        return [], set(), []

    tool_calls = response.tool_calls or []
    if not tool_calls:
        return [], set(), []

    calls: list[tuple[str, str]] = []  # (mcp_name, tool_query), gather와 같은 순서로 짝을 맞춤
    called_tools: set[str] = set()
    tool_calls_used: list[dict] = []
    seen_calls: set[tuple[str, str]] = set()

    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        mcp_name = _TOOL_NAME_TO_MCP_NAME.get(tool_name)
        if mcp_name is None:
            continue

        raw_query = tool_call.get("args", {}).get("query")
        if not isinstance(raw_query, str):
            continue

        tool_query = raw_query.strip()
        if not tool_query or len(tool_query) > _MAX_QUERY_LEN:
            continue

        call_key = (mcp_name, tool_query)
        if call_key in seen_calls:
            continue
        seen_calls.add(call_key)

        calls.append(call_key)
        called_tools.add(mcp_name)
        tool_calls_used.append({"tool": mcp_name, "query": tool_query})
        print(f"mcp_agent tool={mcp_name} query=\"{tool_query}\"")

    if not calls:
        return [], set(), []

    tasks = [
        mcp_client.search_law(q) if name == "search_law" else mcp_client.search_decisions(q)
        for name, q in calls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    sources: list[dict] = []
    fallback_tasks: list = []
    for (mcp_name, tool_query), result in zip(calls, results):
        if isinstance(result, BaseException):
            print(f"[error] mcp_agent MCP 호출 실패: {result}")
            result = []
        filtered = [item for item in result if item.get("score", 0) > 0]
        if filtered:
            sources.extend(filtered)
        elif mcp_name == "search_decisions":
            # korean-law-mcp가 판례를 못 찾았을 때만 lexguard-mcp로 보완 — 법령 검색은 아직
            # lexguard-mcp에 동일한 키워드 검색 tool이 없어(legal_qa_tool은 응답 구조가 달라
            # 별도 파싱 필요) 폴백 대상에서 제외.
            fallback_tasks.append(lexguard_client.search_decisions(tool_query))

    if fallback_tasks:
        fallback_results = await asyncio.gather(*fallback_tasks, return_exceptions=True)
        for result in fallback_results:
            if isinstance(result, BaseException):
                print(f"[error] mcp_agent lexguard-mcp 폴백 호출 실패: {result}")
                continue
            sources.extend(item for item in result if item.get("score", 0) > 0)

    print(f"mcp_agent called_tools={sorted(called_tools)} results={len(sources)}")
    return sources, called_tools, tool_calls_used
