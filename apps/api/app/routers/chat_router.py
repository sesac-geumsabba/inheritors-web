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
    """사용자의 챗봇 질문을 수신하여 MCP로 법령/판례를 조회하고 정제된 답변과 출처 카드 목록을 반환합니다."""
    query = req.message.strip()
    sources: List[Dict[str, Any]] = []

    if not query:
        return ChatResponse(answer="질문을 입력해 주세요.", sources=[])

    is_precedent_query = any(k in query for k in ["판례", "사건", "판결", "대법원", "지방법원"])
    is_law_query = any(k in query for k in ["법", "조문", "신탁", "상속", "증여"])

    if is_precedent_query and not is_law_query:
        sources = await mcp_client.search_decisions(query)
    elif is_law_query and not is_precedent_query:
        sources = await mcp_client.search_law(query)
    else:
        # 두 영역 모두 포함된 질의인 경우 병렬 호출
        laws = await mcp_client.search_law(query)
        decisions = await mcp_client.search_decisions(query)
        sources = (laws[:2] if laws else []) + (decisions[:2] if decisions else [])

    statute_count = sum(1 for s in sources if s.get("source_type") == "statute")
    case_count = sum(1 for s in sources if s.get("source_type") == "case_law")

    answer_parts = [f"안녕하세요! 요청하신 '{query}' 관련 대한민국 법제처 및 대법원 판례 검색 결과입니다.\n"]
    if statute_count > 0:
        answer_parts.append(f"• 📜 법령 정보: 관련 조문 및 법률 데이터 {statute_count}건이 검색되었습니다.")
    if case_count > 0:
        answer_parts.append(f"• ⚖️ 판례 정보: 대법원 및 하급심 판결 데이터 {case_count}건이 조회되었습니다.")

    answer_parts.append("\n자세한 조문 내용 및 사건번호 정보는 아래 출처 카드를 참고해 주세요.")
    answer = "\n".join(answer_parts)

    return ChatResponse(answer=answer, sources=sources)
