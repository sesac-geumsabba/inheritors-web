"""app.mcp_agent.select_and_run() 단위 테스트.

실제 OpenAI/korean-law-mcp에 의존하지 않는다 — tool-calling LLM의 응답(tool_calls)과
mcp_client.search_law/search_decisions를 모킹해서 도구 선택/중복 제거/병렬 실행/오류
폴백 로직만 검증한다. 실제 LLM 판단 품질은 통합 테스트(별도, 이 파일에 포함하지 않음)로 검증한다.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import mcp_agent


def _fake_llm(tool_calls):
    llm = SimpleNamespace()
    llm.ainvoke = AsyncMock(return_value=SimpleNamespace(tool_calls=tool_calls))
    return llm


def _tool_call(name: str, query, call_id: str = "1"):
    return {"name": name, "args": {"query": query}, "id": call_id}


class TestSelectAndRun(unittest.IsolatedAsyncioTestCase):
    async def test_law_tool_only(self):
        law_result = [{"source_type": "statute", "title": "t", "url": "", "snippet": "s", "score": 0.9}]
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm([_tool_call("search_law_tool", "유류분")])),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock(return_value=law_result)) as mock_law,
            patch.object(mcp_agent.mcp_client, "search_decisions", new=AsyncMock()) as mock_decisions,
        ):
            sources, called_tools, tool_calls_used = await mcp_agent.select_and_run("유류분이 뭐야")

        mock_law.assert_awaited_once_with("유류분")
        mock_decisions.assert_not_awaited()
        self.assertEqual(sources, law_result)
        self.assertEqual(called_tools, {"search_law"})
        self.assertEqual(tool_calls_used, [{"tool": "search_law", "query": "유류분"}])

    async def test_precedent_tool_only(self):
        case_result = [{"source_type": "case_law", "title": "t", "url": "", "snippet": "s", "score": 0.8}]
        with (
            patch.object(
                mcp_agent, "_agent_llm", return_value=_fake_llm([_tool_call("search_decisions_tool", "유류분 반환")])
            ),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock()) as mock_law,
            patch.object(mcp_agent.mcp_client, "search_decisions", new=AsyncMock(return_value=case_result)) as mock_decisions,
        ):
            sources, called_tools, _ = await mcp_agent.select_and_run("판례만 알려줘")

        mock_decisions.assert_awaited_once_with("유류분 반환")
        mock_law.assert_not_awaited()
        self.assertEqual(sources, case_result)
        self.assertEqual(called_tools, {"search_decisions"})

    async def test_both_tools_called_and_merged(self):
        law_result = [{"source_type": "statute", "score": 0.9}]
        case_result = [{"source_type": "case_law", "score": 0.8}]
        tool_calls = [
            _tool_call("search_law_tool", "유류분", call_id="1"),
            _tool_call("search_decisions_tool", "유류분 반환", call_id="2"),
        ]
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm(tool_calls)),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock(return_value=law_result)),
            patch.object(mcp_agent.mcp_client, "search_decisions", new=AsyncMock(return_value=case_result)),
        ):
            sources, called_tools, _ = await mcp_agent.select_and_run("유류분과 관련 판례 모두 알려줘")

        self.assertEqual(called_tools, {"search_law", "search_decisions"})
        self.assertCountEqual(sources, law_result + case_result)

    async def test_no_tool_calls_returns_empty(self):
        with patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm([])):
            sources, called_tools, _ = await mcp_agent.select_and_run("부동산 재건축 절차를 알려줘")

        self.assertEqual(sources, [])
        self.assertEqual(called_tools, set())

    async def test_llm_call_failure_falls_back_to_empty(self):
        llm = SimpleNamespace()
        llm.ainvoke = AsyncMock(side_effect=RuntimeError("openai down"))
        with patch.object(mcp_agent, "_agent_llm", return_value=llm):
            sources, called_tools, _ = await mcp_agent.select_and_run("유류분이 뭐야")

        self.assertEqual(sources, [])
        self.assertEqual(called_tools, set())

    async def test_partial_mcp_failure_keeps_successful_result(self):
        case_result = [{"source_type": "case_law", "score": 0.8}]
        tool_calls = [
            _tool_call("search_law_tool", "유류분", call_id="1"),
            _tool_call("search_decisions_tool", "유류분 반환", call_id="2"),
        ]
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm(tool_calls)),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock(side_effect=RuntimeError("mcp error"))),
            patch.object(mcp_agent.mcp_client, "search_decisions", new=AsyncMock(return_value=case_result)),
        ):
            sources, called_tools, _ = await mcp_agent.select_and_run("유류분과 관련 판례 모두 알려줘")

        self.assertEqual(sources, case_result)
        self.assertEqual(called_tools, {"search_law", "search_decisions"})

    async def test_duplicate_tool_and_query_deduped(self):
        law_result = [{"source_type": "statute", "score": 0.9}]
        tool_calls = [
            _tool_call("search_law_tool", "유류분", call_id="1"),
            _tool_call("search_law_tool", " 유류분 ", call_id="2"),
        ]
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm(tool_calls)),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock(return_value=law_result)) as mock_law,
        ):
            sources, called_tools, _ = await mcp_agent.select_and_run("유류분이 뭐야")

        mock_law.assert_awaited_once_with("유류분")
        self.assertEqual(sources, law_result)
        self.assertEqual(called_tools, {"search_law"})

    async def test_different_queries_both_executed(self):
        tool_calls = [
            _tool_call("search_law_tool", "유류분", call_id="1"),
            _tool_call("search_law_tool", "유류분 반환", call_id="2"),
        ]
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm(tool_calls)),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock(return_value=[])) as mock_law,
        ):
            await mcp_agent.select_and_run("유류분이 뭐고 반환은 어떻게 해")

        self.assertEqual(mock_law.await_count, 2)

    async def test_score_filtering(self):
        mixed_result = [
            {"source_type": "statute", "score": 0.9},
            {"source_type": "statute", "score": 0.0},
        ]
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm([_tool_call("search_law_tool", "유류분")])),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock(return_value=mixed_result)),
        ):
            sources, _, _ = await mcp_agent.select_and_run("유류분이 뭐야")

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["score"], 0.9)

    async def test_unknown_tool_name_ignored(self):
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm([_tool_call("unknown_tool", "유류분")])),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock()) as mock_law,
            patch.object(mcp_agent.mcp_client, "search_decisions", new=AsyncMock()) as mock_decisions,
        ):
            sources, called_tools, _ = await mcp_agent.select_and_run("유류분이 뭐야")

        mock_law.assert_not_awaited()
        mock_decisions.assert_not_awaited()
        self.assertEqual(sources, [])
        self.assertEqual(called_tools, set())

    async def test_precedent_fallback_used_when_primary_empty(self):
        """korean-law-mcp가 0건이면 lexguard-mcp로 보완 호출한다."""
        fallback_result = [{"source_type": "case_law", "title": "lexguard", "score": 0.9}]
        with (
            patch.object(
                mcp_agent, "_agent_llm", return_value=_fake_llm([_tool_call("search_decisions_tool", "유류분 반환")])
            ),
            patch.object(mcp_agent.mcp_client, "search_decisions", new=AsyncMock(return_value=[])),
            patch.object(
                mcp_agent.lexguard_client, "search_decisions", new=AsyncMock(return_value=fallback_result)
            ) as mock_fallback,
        ):
            sources, called_tools, _ = await mcp_agent.select_and_run("판례만 알려줘")

        mock_fallback.assert_awaited_once_with("유류분 반환")
        self.assertEqual(sources, fallback_result)
        self.assertEqual(called_tools, {"search_decisions"})

    async def test_precedent_fallback_skipped_when_primary_has_results(self):
        """korean-law-mcp가 결과를 이미 찾았으면 lexguard-mcp는 호출하지 않는다."""
        case_result = [{"source_type": "case_law", "score": 0.8}]
        with (
            patch.object(
                mcp_agent, "_agent_llm", return_value=_fake_llm([_tool_call("search_decisions_tool", "유류분 반환")])
            ),
            patch.object(mcp_agent.mcp_client, "search_decisions", new=AsyncMock(return_value=case_result)),
            patch.object(mcp_agent.lexguard_client, "search_decisions", new=AsyncMock()) as mock_fallback,
        ):
            sources, _, _ = await mcp_agent.select_and_run("판례만 알려줘")

        mock_fallback.assert_not_awaited()
        self.assertEqual(sources, case_result)

    async def test_law_tool_has_no_fallback(self):
        """search_law는 lexguard-mcp에 동일한 키워드 검색 tool이 없어 폴백하지 않는다(4.8절)."""
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm([_tool_call("search_law_tool", "유류분")])),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock(return_value=[])),
            patch.object(mcp_agent.lexguard_client, "search_decisions", new=AsyncMock()) as mock_fallback,
        ):
            sources, _, _ = await mcp_agent.select_and_run("유류분이 뭐야")

        mock_fallback.assert_not_awaited()
        self.assertEqual(sources, [])

    async def test_precedent_fallback_error_keeps_empty(self):
        """lexguard-mcp 호출 자체가 실패해도 전체 요청은 막히지 않는다."""
        with (
            patch.object(
                mcp_agent, "_agent_llm", return_value=_fake_llm([_tool_call("search_decisions_tool", "유류분 반환")])
            ),
            patch.object(mcp_agent.mcp_client, "search_decisions", new=AsyncMock(return_value=[])),
            patch.object(
                mcp_agent.lexguard_client, "search_decisions", new=AsyncMock(side_effect=RuntimeError("lexguard down"))
            ),
        ):
            sources, called_tools, _ = await mcp_agent.select_and_run("판례만 알려줘")

        self.assertEqual(sources, [])
        self.assertEqual(called_tools, {"search_decisions"})

    async def test_empty_or_non_string_query_ignored(self):
        tool_calls = [
            _tool_call("search_law_tool", "   ", call_id="1"),
            _tool_call("search_law_tool", 123, call_id="2"),
        ]
        with (
            patch.object(mcp_agent, "_agent_llm", return_value=_fake_llm(tool_calls)),
            patch.object(mcp_agent.mcp_client, "search_law", new=AsyncMock()) as mock_law,
        ):
            sources, called_tools, _ = await mcp_agent.select_and_run("유류분이 뭐야")

        mock_law.assert_not_awaited()
        self.assertEqual(sources, [])
        self.assertEqual(called_tools, set())


if __name__ == "__main__":
    unittest.main()
