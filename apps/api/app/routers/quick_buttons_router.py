from fastapi import APIRouter, HTTPException

from app.quick_buttons import (
    PRESET_DATA,
    QuickButtonOption,
    QuickButtonType,
    QuickPresetResponse,
)

router = APIRouter(prefix="/quick-buttons", tags=["Quick Buttons"])


@router.get("", response_model=list[QuickButtonOption])
def list_quick_buttons() -> list[QuickButtonOption]:
    """사용 가능한 Quick 버튼 목록 및 해당 버튼의 프리셋 질의정보를 반환합니다."""
    return [
        QuickButtonOption(
            id=key,
            label=data["label"],
            description=data["description"],
            preset_query=data["preset_query"],
        )
        for key, data in PRESET_DATA.items()
    ]


@router.get("/{button_type}", response_model=QuickPresetResponse)
def get_quick_button_preset(button_type: QuickButtonType) -> QuickPresetResponse:
    """특정 Quick 버튼 선택 시 해당 카테고리의 프리셋 질의 및 관련 추천 문서 카드 목록을 반환합니다."""
    if button_type not in PRESET_DATA:
        raise HTTPException(status_code=404, detail="Quick button option not found")

    data = PRESET_DATA[button_type]
    return QuickPresetResponse(
        button_type=button_type,
        preset_query=data["preset_query"],
        documents=data["documents"],
    )
