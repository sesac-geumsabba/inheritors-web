from typing import Any, Dict, List
from fastapi import APIRouter
from pydantic import BaseModel

from app.mcp_client import KoreanLawMCPClient

router = APIRouter(prefix="/api/chat", tags=["Chatbot"])
mcp_client = KoreanLawMCPClient()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]


@router.post("", response_model=ChatResponse, summary="챗봇 메시지 전송 및 MCP 법령/판례 연동")
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """사용자의 챗봇 질문을 수신하여 MCP로 법령/판례를 조회하고 답변과 출처 카드 목록을 반환합니다."""
    query = req.message.strip()
    sources: List[Dict[str, Any]] = []

    if not query:
        return ChatResponse(answer="질문을 입력해 주세요.", sources=[])

    # 판례 또는 법령 질문 감지 시 MCP 호출
    if "판례" in query or "사건" in query or "판결" in query:
        sources = await mcp_client.search_decisions(query)
    elif "법" in query or "조문" in query or "신탁" in query or "상속" in query:
        sources = await mcp_client.search_law(query)
    else:
        # 기본 법령 및 판례 종합 조회
        sources = await mcp_client.search_law(query)

    answer = f"'{query}'에 대한 법령/판례 검색 결과입니다. 상속 및 유언대용신탁 관련 법적 근거는 하단 출처 카드를 참고해 주세요."

    return ChatResponse(answer=answer, sources=sources)
