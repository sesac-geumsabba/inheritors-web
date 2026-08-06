"""대화 기반 상담 리포트 — chat_messages를 근거로 자산/상담 요약/리스크를 LLM이 추출한다.

FN-CORE-01 원안(3단계 자산×특약 선택 위저드)과 달리 별도 입력 폼 없이, 지금까지의
/chat, /chat/openai 대화 내용에서 바로 생성한다. DB에 저장하지 않고 요청마다 다시
생성한다 — 대화가 이어지면 내용이 바뀌므로 캐싱하면 오히려 오래된 리포트를 보여줄
위험이 있고, session당 몇 번 안 불릴 기능이라 재생성 비용이 문제될 규모가 아니다.
"""

import os
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

# "6-7턴 이상"의 하한값 채택 — 상담이 이 정도는 쌓여야 요약할 내용이 생긴다.
MIN_USER_TURNS_FOR_REPORT = 6

REPORT_DISCLAIMER = (
    "본 리포트는 상담 대화 내용을 바탕으로 자동 생성된 참고용 정보이며, "
    "법률/세무 자문을 대체하지 않습니다. 정확한 판단은 반드시 전문가와 상담하시기 바랍니다."
)

_SYSTEM_PROMPT = """당신은 유언대용신탁 상담 챗봇의 상담 내용을 정리하는 어시스턴트다.
아래는 사용자와 챗봇 간의 실제 상담 대화 전체다. 이 대화에서 실제로 언급된 내용만
근거로 삼아 다음을 작성하라:

1. summary: 지금까지 상담에서 다룬 내용을 2~3문장으로 요약
2. assets: 대화에서 사용자가 언급한 자산(부동산/예금/주식 등)만 추출. 종류와, 언급됐다면
   금액/규모도 함께. 대화에 나오지 않은 자산은 절대 지어내지 마라 — 없으면 빈 배열.
3. total_estimate: 자산 금액이 언급된 경우에만 대략적인 합계를 문자열로 (예: "약 15억 원").
   금액이 하나도 언급 안 됐으면 null.
4. risks: 대화에서 실제로 드러난 법률/세무 쟁점만 리스크로 정리 (예: 특정 자녀에게만
   증여 언급 → 유류분 반환 청구 위험). 대화에 근거가 없는 일반론적 리스크는 만들어내지 마라.

대화에 없는 내용을 추측하거나 지어내지 마라. 근거 없는 항목을 억지로 채우지 말고
빈 배열/null로 두는 편이 낫다."""


class AssetItem(BaseModel):
    label: str = Field(description="자산 종류 (예: '부동산 (아파트)', '현금 및 예금')")
    amount: str | None = Field(default=None, description="언급된 금액/규모. 대화에 없으면 null")


class RiskItem(BaseModel):
    title: str = Field(description="리스크 제목 (예: '유류분 반환 청구 소송 위험')")
    description: str = Field(description="왜 문제가 될 수 있는지, 대화 맥락에 근거한 설명")


class _LLMReport(BaseModel):
    """구조화 출력 스키마 — disclaimer는 여기 없음. 필드로 두면 LLM이 고지 문구를 자기
    말로 바꿔 쓴다(실측 확인: "법률 및 세무 자문은 제공하지 않음을 알려드립니다" 같은
    패러프레이즈가 나옴) — 컴플라이언스 문구는 모델 재량이 아니라 항상 REPORT_DISCLAIMER
    그대로여야 하므로 아예 생성 대상에서 빼고 ConsultationReport 조립 시 고정값으로 붙인다."""

    summary: str = Field(description="상담 내용 2~3문장 요약")
    assets: list[AssetItem] = Field(default_factory=list)
    total_estimate: str | None = Field(default=None)
    risks: list[RiskItem] = Field(default_factory=list)


class ConsultationReport(BaseModel):
    summary: str
    assets: list[AssetItem] = Field(default_factory=list)
    total_estimate: str | None = Field(default=None)
    risks: list[RiskItem] = Field(default_factory=list)
    disclaimer: str = REPORT_DISCLAIMER


@lru_cache(maxsize=1)
def _report_llm():
    return ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=0,
    ).with_structured_output(_LLMReport)


def _load_conversation(db: Session, session_id: int) -> list[tuple[str, str]]:
    rows = db.execute(
        text(
            "SELECT role, content FROM chat_messages "
            "WHERE session_id = :sid AND role IN ('user', 'assistant') AND content != '' "
            "ORDER BY id"
        ),
        {"sid": session_id},
    ).all()
    return [(r.role, r.content) for r in rows]


async def _generate_from_turns(turns: list[tuple[str, str]]) -> ConsultationReport | None:
    """DB에서 분리한 순수 로직 — 턴 수 가드 + LLM 호출만 담당해서 DB 없이 단위 테스트 가능."""
    user_turns = sum(1 for role, _ in turns if role == "user")
    if user_turns < MIN_USER_TURNS_FOR_REPORT:
        return None

    conversation_text = "\n".join(
        f"{'사용자' if role == 'user' else '챗봇'}: {content}" for role, content in turns
    )
    llm_result = await _report_llm().ainvoke(
        [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=conversation_text)]
    )
    return ConsultationReport(**llm_result.model_dump())


async def generate_report(db: Session, session_id: int) -> ConsultationReport | None:
    """대화가 MIN_USER_TURNS_FOR_REPORT 미만이면 None — 라우터가 이걸로 아직 이르다는
    응답을 내려준다. 대화 자체가 없는 session_id(존재 자체 검증은 라우터 책임)도 여기선
    그냥 빈 대화로 취급해 None을 반환한다."""
    turns = _load_conversation(db, session_id)
    return await _generate_from_turns(turns)
