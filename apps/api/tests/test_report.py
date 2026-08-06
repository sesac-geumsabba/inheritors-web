"""app.report._generate_from_turns() 단위 테스트.

DB에 의존하는 generate_report/_load_conversation은 다루지 않는다(이 리포의 다른 테스트와
같은 관례 — test_chat_shared.py 참고). LLM 호출(_report_llm)만 모킹해서 턴 수 가드
로직을 검증한다.
"""

import unittest
from unittest.mock import AsyncMock, patch

from app import report


def _turns(user_count: int) -> list[tuple[str, str]]:
    turns = []
    for i in range(user_count):
        turns.append(("user", f"질문 {i}"))
        turns.append(("assistant", f"답변 {i}"))
    return turns


class TestGenerateFromTurns(unittest.IsolatedAsyncioTestCase):
    async def test_below_threshold_returns_none_without_calling_llm(self):
        with patch.object(report, "_report_llm") as mock_llm_factory:
            result = await report._generate_from_turns(_turns(report.MIN_USER_TURNS_FOR_REPORT - 1))

        mock_llm_factory.assert_not_called()
        self.assertIsNone(result)

    async def test_at_threshold_calls_llm(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=report._LLMReport(summary="요약"))
        with patch.object(report, "_report_llm", return_value=mock_llm):
            result = await report._generate_from_turns(_turns(report.MIN_USER_TURNS_FOR_REPORT))

        mock_llm.ainvoke.assert_awaited_once()
        self.assertIsInstance(result, report.ConsultationReport)
        self.assertEqual(result.summary, "요약")

    async def test_disclaimer_always_fixed_regardless_of_llm_output(self):
        """LLM이 disclaimer를 생성하지 않으므로(스키마에서 제외) 항상 고정 문구가 붙는다."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=report._LLMReport(summary="요약"))
        with patch.object(report, "_report_llm", return_value=mock_llm):
            result = await report._generate_from_turns(_turns(report.MIN_USER_TURNS_FOR_REPORT))

        self.assertEqual(result.disclaimer, report.REPORT_DISCLAIMER)

    async def test_conversation_text_includes_both_roles(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=report._LLMReport(summary="요약"))
        with patch.object(report, "_report_llm", return_value=mock_llm):
            await report._generate_from_turns(_turns(report.MIN_USER_TURNS_FOR_REPORT))

        messages = mock_llm.ainvoke.await_args.args[0]
        conversation_message = messages[1].content
        self.assertIn("사용자: 질문 0", conversation_message)
        self.assertIn("챗봇: 답변 0", conversation_message)


class TestConsultationReportDefaults(unittest.TestCase):
    def test_disclaimer_defaults_and_empty_lists(self):
        r = report.ConsultationReport(summary="요약")
        self.assertEqual(r.disclaimer, report.REPORT_DISCLAIMER)
        self.assertEqual(r.assets, [])
        self.assertEqual(r.risks, [])
        self.assertIsNone(r.total_estimate)


if __name__ == "__main__":
    unittest.main()
