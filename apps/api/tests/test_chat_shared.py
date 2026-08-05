"""app.chat_shared의 MCP 관련 순수 로직 단위 테스트 (_mcp_reason, fetch_external_sources).

DB에 의존하는 나머지 chat_shared 함수(create_session, save_message 등)는 다루지 않는다.
"""

import unittest
from unittest.mock import AsyncMock, patch

from app import chat_shared


class TestMcpReason(unittest.TestCase):
    def test_empty_tool_calls_returns_empty_string(self):
        self.assertEqual(chat_shared._mcp_reason([]), "")

    def test_single_law_call(self):
        reason = chat_shared._mcp_reason([{"tool": "search_law", "query": "유류분"}])
        self.assertEqual(reason, "법령 '유류분' 검색을 위해 호출")

    def test_multiple_calls_joined(self):
        reason = chat_shared._mcp_reason(
            [
                {"tool": "search_law", "query": "유류분"},
                {"tool": "search_decisions", "query": "유류분 반환"},
            ]
        )
        self.assertEqual(reason, "법령 '유류분' · 판례 '유류분 반환' 검색을 위해 호출")


class TestFetchExternalSources(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_called_true_even_when_no_sources_survive_filtering(self):
        with patch.object(
            chat_shared, "select_and_run", new=AsyncMock(return_value=([], {"search_decisions"}, [{"tool": "search_decisions", "query": "유류분 반환"}]))
        ):
            sources, precedent_only, mcp_meta = await chat_shared.fetch_external_sources("판례만 알려줘")

        self.assertEqual(sources, [])
        # 판례 도구를 선택했지만 실제 결과가 없으므로(호출 실패/0건) 내부 RAG 폴백을 위해 False
        self.assertFalse(precedent_only)
        # 그래도 MCP가 "호출은 됐다"는 사실은 남아있어야 프론트에 보여줄 수 있음
        self.assertEqual(mcp_meta, {"called": True, "tools": ["search_decisions"], "reason": "판례 '유류분 반환' 검색을 위해 호출"})

    async def test_precedent_only_true_when_case_law_source_present(self):
        case_result = [{"source_type": "case_law", "title": "t", "url": "", "snippet": "s", "score": 0.8}]
        with patch.object(
            chat_shared, "select_and_run", new=AsyncMock(return_value=(case_result, {"search_decisions"}, [{"tool": "search_decisions", "query": "유류분 반환"}]))
        ):
            sources, precedent_only, mcp_meta = await chat_shared.fetch_external_sources("판례만 알려줘")

        self.assertEqual(sources, case_result)
        self.assertTrue(precedent_only)
        self.assertTrue(mcp_meta["called"])

    async def test_mcp_not_called(self):
        with patch.object(chat_shared, "select_and_run", new=AsyncMock(return_value=([], set(), []))):
            sources, precedent_only, mcp_meta = await chat_shared.fetch_external_sources("부동산 재건축 절차를 알려줘")

        self.assertEqual(sources, [])
        self.assertFalse(precedent_only)
        self.assertEqual(mcp_meta, {"called": False, "tools": [], "reason": ""})


if __name__ == "__main__":
    unittest.main()
