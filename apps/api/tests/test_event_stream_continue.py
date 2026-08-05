"""app.chat_shared.event_stream()의 이어보기(continue) 관련 로직 단위 테스트.

핵심 검증 대상: 800자 페이싱 컷이 "실제로 더 남은 내용이 있을 때만" 이어보기 버튼
(event: awaiting_continue)을 띄우는지, 그리고 continue_count가 MAX_CONTINUE_DEPTH에
도달하면 더 남은 내용이 있어도 버튼을 더 이상 띄우지 않는지 — 이어보기 무한 반복 버그의
핵심 회귀 방지 테스트다. DB는 MagicMock으로 대체해 실제 연결 없이 검증한다.
"""

import unittest
from unittest.mock import MagicMock

from app import chat_shared


def _make_db(message_id: int = 42) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.scalar_one.return_value = message_id
    return db


def _events(chunks_of_stream) -> list[tuple[str, str]]:
    """event_stream()이 만든 SSE 텍스트 블록들을 (event_type, data) 튜플 리스트로 파싱."""
    events = []
    for block in chunks_of_stream:
        event_type = "message"
        data_lines = []
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[len("event: "):]
            elif line.startswith("data: "):
                data_lines.append(line[len("data: "):])
        events.append((event_type, "\n".join(data_lines)))
    return events


class TestEventStreamContinueGating(unittest.TestCase):
    def test_natural_end_at_pacing_boundary_no_continue_button(self):
        """800자 컷에 걸렸지만 그 뒤로 실제 토큰이 없으면(자연스러운 끝) 버튼을 띄우지 않는다."""
        long_sentence = "가" * chat_shared.PAGE_CHAR_LIMIT + "."

        def tokens():
            yield long_sentence

        events = _events(
            list(
                chat_shared.event_stream(
                    _make_db(), 1, tokens(), [], [], emit_sources=False, continue_count=0
                )
            )
        )
        event_types = [e for e, _ in events]
        self.assertNotIn("awaiting_continue", event_types)
        # followup 문구("더 설명해드릴까요?")도 붙지 않아야 한다.
        combined = "".join(data for etype, data in events if etype == "message")
        self.assertNotIn("더 설명해드릴까요", combined)

    def test_real_remaining_content_shows_continue_button(self):
        """800자 컷 이후에도 실제로 더 올 토큰이 있으면 버튼을 띄운다."""
        long_sentence = "가" * chat_shared.PAGE_CHAR_LIMIT + "."

        def tokens():
            yield long_sentence
            yield "이어지는 내용입니다."

        events = _events(
            list(
                chat_shared.event_stream(
                    _make_db(), 1, tokens(), [], [], emit_sources=False, continue_count=0
                )
            )
        )
        awaiting = [data for etype, data in events if etype == "awaiting_continue"]
        self.assertEqual(len(awaiting), 1)
        self.assertIn('"continue_count": 0', awaiting[0])

    def test_continue_depth_cap_suppresses_button_even_with_more_content(self):
        """continue_count가 상한에 도달하면 더 남은 내용이 있어도 버튼을 띄우지 않는다."""
        long_sentence = "가" * chat_shared.PAGE_CHAR_LIMIT + "."

        def tokens():
            yield long_sentence
            yield "이어지는 내용입니다."

        events = _events(
            list(
                chat_shared.event_stream(
                    _make_db(),
                    1,
                    tokens(),
                    [],
                    [],
                    emit_sources=False,
                    continue_count=chat_shared.MAX_CONTINUE_DEPTH,
                )
            )
        )
        event_types = [e for e, _ in events]
        self.assertNotIn("awaiting_continue", event_types)

    def test_short_answer_never_hits_pacing_limit(self):
        """애초에 800자를 안 넘는 짧은 답변은 페이싱 컷 자체가 안 걸려 버튼이 없다."""

        def tokens():
            yield "짧은 답변입니다."

        events = _events(
            list(
                chat_shared.event_stream(
                    _make_db(), 1, tokens(), [], [], emit_sources=False, continue_count=0
                )
            )
        )
        event_types = [e for e, _ in events]
        self.assertNotIn("awaiting_continue", event_types)


if __name__ == "__main__":
    unittest.main()
