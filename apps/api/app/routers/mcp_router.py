from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.mcp_client import mcp_client

router = APIRouter(prefix="/api/mcp", tags=["MCP Korean Law"])


class VerifyCitationsRequest(BaseModel):
    text: str


@router.get("/law", summary="법령/조문 검색 (korean-law-mcp)")
async def search_law(
    query: str = Query(..., description="검색할 법령명 또는 조문 키워드"),
    timeout: float = Query(3.0, description="타임아웃(초)"),
) -> List[Dict[str, Any]]:
    """korean-law-mcp search_law 도구를 호출하여 법령 정보를 조회하고 message_sources 포맷으로 반환합니다."""
    return await mcp_client.search_law(query=query, timeout=timeout)


@router.get("/decisions", summary="판례 검색 (korean-law-mcp)")
async def search_decisions(
    query: str = Query(..., description="검색할 판례 키워드 또는 사건번호"),
    domain: str = Query("precedent", description="판례 도메인"),
    timeout: float = Query(3.0, description="타임아웃(초)"),
) -> List[Dict[str, Any]]:
    """korean-law-mcp search_decisions 도구를 호출하여 판례 정보를 조회하고 message_sources 포맷으로 반환합니다."""
    return await mcp_client.search_decisions(query=query, domain=domain, timeout=timeout)


@router.post("/verify", summary="답변 조문/판례 인용 환각 검증 (korean-law-mcp)")
async def verify_citations(
    req: VerifyCitationsRequest,
    timeout: float = Query(3.0, description="타임아웃(초)"),
) -> Dict[str, Any]:
    """korean-law-mcp verify_citations 도구를 호출하여 생성된 답변 내 조문/판례 실존 및 환각 여부를 검증합니다."""
    return await mcp_client.verify_citations(text=req.text, timeout=timeout)
