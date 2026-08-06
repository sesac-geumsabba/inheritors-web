from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.report import MIN_USER_TURNS_FOR_REPORT, ConsultationReport, generate_report

router = APIRouter(prefix="/chat", tags=["Report"])


@router.get("/{session_id}/report", response_model=ConsultationReport)
async def get_report(session_id: int, db: Session = Depends(get_db)) -> ConsultationReport:
    session_exists = db.execute(
        text("SELECT 1 FROM chat_sessions WHERE id = :sid"), {"sid": session_id}
    ).first()
    if session_exists is None:
        raise HTTPException(status_code=404, detail="session not found")

    try:
        report = await generate_report(db, session_id)
    except Exception as e:
        # OpenAI 오류/구조화 출력 실패 등 — 프론트가 안내 메시지 + 재시도 버튼을 보여줄 수
        # 있도록 500이 아니라 502(업스트림 실패)로 구분해서 내려준다.
        raise HTTPException(status_code=502, detail=f"리포트 생성 중 오류가 발생했습니다: {e}") from e

    if report is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "not_enough_turns",
                "min_turns": MIN_USER_TURNS_FOR_REPORT,
                "message": f"상담이 아직 짧아 리포트를 만들 수 없습니다 (최소 {MIN_USER_TURNS_FOR_REPORT}턴 필요).",
            },
        )
    return report
