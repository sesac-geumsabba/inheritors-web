from enum import Enum
from pydantic import BaseModel


class QuickButtonType(str, Enum):
    BTN_PRECEDENT = "BTN_PRECEDENT"
    BTN_CASES = "BTN_CASES"
    BTN_TRUST_TYPES = "BTN_TRUST_TYPES"


class QuickButtonOption(BaseModel):
    id: QuickButtonType
    label: str
    description: str
    preset_query: str


class DocumentCard(BaseModel):
    id: str
    title: str
    category: QuickButtonType
    snippet: str
    source_url: str | None = None


class QuickPresetResponse(BaseModel):
    button_type: QuickButtonType
    preset_query: str
    documents: list[DocumentCard]


PRESET_DATA: dict[QuickButtonType, dict] = {
    QuickButtonType.BTN_PRECEDENT: {
        "label": "대표 판례",
        "description": "유류분 반환 청구 및 유언대용신탁 관련 핵심 법원 판례",
        "preset_query": "유언대용신탁과 유류분 반환 청구 관련 대표 판례를 알려주세요.",
        "documents": [
            {
                "id": "prec-01",
                "title": "대법원 2024. 4. 25. 선고 2023다298655 판결",
                "category": QuickButtonType.BTN_PRECEDENT,
                "snippet": "유언대용신탁 재산이 유류분 반환 대상에 포함되는지 여부에 대한 대법원의 주요 판단 기준 및 산정 방식.",
                "source_url": "https://glaw.scourt.go.kr",
            },
            {
                "id": "prec-02",
                "title": "서울고법 2022나2012345 판결",
                "category": QuickButtonType.BTN_PRECEDENT,
                "snippet": "위탁자 사망 전 1년 이내에 수익권이 지정된 유언대용신탁 계약의 반환 범위 해석.",
                "source_url": "https://glaw.scourt.go.kr",
            },
            {
                "id": "prec-03",
                "title": "대법원 2020다273872 판결",
                "category": QuickButtonType.BTN_PRECEDENT,
                "snippet": "신탁재산의 독립성과 상속재산 분할 대상 제외 여부에 관한 판례.",
                "source_url": "https://glaw.scourt.go.kr",
            },
        ],
    },
    QuickButtonType.BTN_CASES: {
        "label": "실생활 사례",
        "description": "자녀 간 상속 분쟁 예방 및 실생활 신탁 활용 사례",
        "preset_query": "시니어 자산가가 자녀 간 상속 분쟁을 예방하기 위해 신탁을 활용한 실생활 사례를 보여주세요.",
        "documents": [
            {
                "id": "case-01",
                "title": "사례 1: 재혼 가정 상속 분쟁 예방 신탁",
                "category": QuickButtonType.BTN_CASES,
                "snippet": "배우자 사후 재산이 전처 자녀와 후처 자녀 간 갈등 없이 승계되도록 수익권을 2단계로 설정한 사례.",
            },
            {
                "id": "case-02",
                "title": "사례 2: 장애/치매 대비 부양 조건부 신탁",
                "category": QuickButtonType.BTN_CASES,
                "snippet": "본인의 치매 발생 시 병원비 및 생활비를 안정적으로 지급받도록 금융회사와 맺은 신탁 계약 사례.",
            },
            {
                "id": "case-03",
                "title": "사례 3: 가업 승계 및 주식 신탁",
                "category": QuickButtonType.BTN_CASES,
                "snippet": "중소기업 대표가 의결권과 배당권을 분리하여 특정 자녀에게 경영권을 안정적으로 승계한 사례.",
            },
        ],
    },
    QuickButtonType.BTN_TRUST_TYPES: {
        "label": "신탁 특약 종류",
        "description": "유언대용신탁의 맞춤형 특약 유형 안내",
        "preset_query": "유언대용신탁에서 설정할 수 있는 주요 특약 종류에는 무엇이 있나요?",
        "documents": [
            {
                "id": "trust-01",
                "title": "수익자 연속 신탁 특약",
                "category": QuickButtonType.BTN_TRUST_TYPES,
                "snippet": "1차 수익자(본인) 사후 2차 수익자(배우자), 3차 수익자(자녀)로 순차적 수익권이 이전되는 특약.",
            },
            {
                "id": "trust-02",
                "title": "정기 지급 및 조건부 지급 특약",
                "category": QuickButtonType.BTN_TRUST_TYPES,
                "snippet": "사후 자녀에게 매월 일정 금액을 지급하거나, 특정 연령 달성/혼인 시 분할 지급하는 특약.",
            },
            {
                "id": "trust-03",
                "title": "의료/간병비 전용 집행 특약",
                "category": QuickButtonType.BTN_TRUST_TYPES,
                "snippet": "위탁자 병환 시 증빙된 의료비·간병비 항목에 한해 수탁자가 직접 병원에 지급하는 특약.",
            },
        ],
    },
}
