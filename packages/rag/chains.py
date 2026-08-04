"""disclaimer + 신탁 자료를 조립해 LLM(Ollama)에 주입하는 RAG 체인. 컨텍스트에 없는 내용은 답하지 않도록 강제."""

import os
from collections.abc import Iterator
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session

from packages.rag.retriever import DEFAULT_TOP_K, RetrievedChunk, search_chunks

# ponytail: 스모크 테스트 기준값 — 무관 질의("저녁 메뉴") 0.372 vs 관련 질의("상속세 신고기한") 0.653.
# 두 샘플만으로 정한 값이라 실제 질의 로그 쌓이면 재조정 필요.
NO_CONTEXT_THRESHOLD = 0.45
NO_CONTEXT_MESSAGE = (
    "문의하신 내용과 관련된 자료를 찾지 못했습니다. "
    "다른 표현으로 다시 질문해 주시거나 은행 PB 상담을 이용해 주세요."
)

SYSTEM_PROMPT = """당신은 유언대용신탁 상담 챗봇입니다.
아래 [문서]에 있는 내용만 근거로 답변하세요. [문서]에 없는 내용은 추측하거나 지어내지 말고 모른다고 답하세요.
답변은 본 서비스가 법률/세무 자문이 아닌 정보 제공 목적임을 자연스럽게 밝히고, 참고한 문서명을 함께 표시하세요."""


@lru_cache(maxsize=1)
def _llm() -> ChatOllama:
    return ChatOllama(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.environ.get(
            "OLLAMA_MODEL", "hf.co/heegyu/EEVE-Korean-Instruct-10.8B-v1.0-GGUF:Q4_K_M"
        ),
        temperature=0.2,
    )


def _build_context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[{i + 1}] ({c.file_name} p.{c.page or '-'}) {c.content}" for i, c in enumerate(chunks)
    )


def stream_answer(
    db: Session,
    query: str,
    query_embedding: list[float],
    top_k: int = DEFAULT_TOP_K,
) -> tuple[Iterator[str], list[RetrievedChunk]]:
    """답변 토큰 스트림과, message_sources 기록용으로 실제 인용된 청크 목록을 함께 반환.

    query_embedding은 호출 측(라우터)이 이미 계산해 chat_messages 저장에도 쓰는 값을 그대로 받는다
    (같은 질의를 두 번 임베딩하지 않기 위해).
    """
    chunks = search_chunks(db, query_embedding, top_k)
    if not chunks or chunks[0].score < NO_CONTEXT_THRESHOLD:
        return iter([NO_CONTEXT_MESSAGE]), []

    messages = [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\n[문서]\n{_build_context(chunks)}"),
        HumanMessage(content=query),
    ]

    def _tokens() -> Iterator[str]:
        for chunk in _llm().stream(messages):
            if chunk.content:
                yield chunk.content

    return _tokens(), chunks
