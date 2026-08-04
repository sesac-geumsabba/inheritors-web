"""disclaimer + 신탁 자료를 조립해 LLM(Ollama)에 주입하는 RAG 체인. 컨텍스트에 없는 내용은 답하지 않도록 강제."""

import os
import re
from collections.abc import Iterator
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session

from packages.rag.retriever import DEFAULT_TOP_K, RetrievedChunk, search_chunks

# ponytail: 설명서/계약서/상속증여세 3카테고리 + 경계(금융이지만 무관)/완전무관 질의 11개로 보정.
# 관련 질의 top-1 최소 0.621, 무관·경계 질의 top-1 최대 0.442 — 그 사이 값으로 마진 확보.
# 실제 질의 로그 쌓이면 재조정 필요 (test_retriever.py의 CASES가 회귀 체크 역할).
NO_CONTEXT_THRESHOLD = 0.5
NO_CONTEXT_MESSAGE = (
    "문의하신 내용과 관련된 자료를 찾지 못했습니다. "
    "다른 표현으로 다시 질문해 주시거나 은행 PB 상담을 이용해 주세요."
)

SYSTEM_PROMPT = """당신은 유언대용신탁 상담 챗봇입니다.
아래 [문서]에 있는 내용만 근거로 답변하세요. [문서]에 없는 내용은 추측하거나 지어내지 말고 모른다고 답하세요.
답변 마지막에 "신뢰도: 90%" 같은 confidence score를 절대 붙이지 마세요. 그런 수치는 근거가 없습니다.
답변은 본 서비스가 법률/세무 자문이 아닌 정보 제공 목적임을 자연스럽게 밝히고, 참고한 문서명을 함께 표시하세요."""


@lru_cache(maxsize=1)
def _llm() -> ChatOllama:
    return ChatOllama(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.environ.get(
            "OLLAMA_MODEL", "hf.co/gchrisoh/EEVE-Korean-Instruct-10.8B-v1.0-Q4_K_M-GGUF"
        ),
        temperature=0.2,
        # ponytail: 실측 중 반복 루프(같은 문단을 계속 재생성)로 60초 넘게 안 끝나는 응답 발생.
        # repeat_penalty=1.3은 루프는 막았지만 컨텍스트 인용을 회피(과도한 페널티로 문서 문구
        # 재사용까지 억제되어 "문서에 없다"고 답하는 회귀 발생)해서 1.15로 낮춤.
        # 반복 단위가 토큰이 아니라 문단(수십~백여 토큰) 블록이라 기본 repeat_last_n(64)로는
        # 못 잡아서 256으로 확장 — 페널티 강도는 그대로 두고 참조 범위만 넓힘.
        # num_predict가 최악의 경우에도 강제 종료되는 진짜 안전망 — repeat_penalty와 역할 분리.
        repeat_penalty=1.15,
        repeat_last_n=256,
        num_predict=768,
        # Ollama 기본값(5분 유휴 후 언로드)이면 트래픽 공백 뒤 첫 요청마다 콜드 로드(수 초) 발생 —
        # "3초 이내 스트리밍 시작" 요구사항 때문에 항상 메모리에 유지.
        keep_alive=-1,
    )


def warm_up() -> None:
    """서버 기동 시 1회 호출해 모델을 메모리에 미리 올려둔다 (첫 실사용자가 콜드 로드를 겪지 않도록)."""
    _llm().invoke("ping")


# ponytail: 프롬프트로 "신뢰도: 90%" 같은 근거 없는 confidence score를 붙이지 말라고 지시해도
# 실측 3/3에서 모델이 무시하고 계속 붙임 (10.8B 양자화 모델이라 지시 준수가 불완전) —
# 답변 끝에 붙기도, 맨 앞에 붙기도 해서 양쪽 다 걸러야 함.
# 프롬프트만 믿지 않고 스트림 앞/뒷부분을 소량 지연 버퍼링해 결정적으로 제거한다.
_JUNK_CORE = r"[\[\(【]?\s*(신뢰도|confidence)\s*[:：]?\s*\d{1,3}\s*%\s*[\]\)】]?\s*"
_LEADING_JUNK_PATTERN = re.compile(r"^" + _JUNK_CORE, re.IGNORECASE)
_TRAILING_JUNK_PATTERN = re.compile(_JUNK_CORE + r"$", re.IGNORECASE)
_TAIL_BUFFER_SIZE = 40


def _strip_confidence_score(tokens: Iterator[str]) -> Iterator[str]:
    buffer = ""
    head_checked = False
    for token in tokens:
        buffer += token
        if len(buffer) > _TAIL_BUFFER_SIZE:
            flush_len = len(buffer) - _TAIL_BUFFER_SIZE
            chunk = buffer[:flush_len]
            if not head_checked:
                chunk = _LEADING_JUNK_PATTERN.sub("", chunk)
                head_checked = True
            yield chunk
            buffer = buffer[flush_len:]
    tail = buffer if head_checked else _LEADING_JUNK_PATTERN.sub("", buffer)
    yield _TRAILING_JUNK_PATTERN.sub("", tail).rstrip()


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

    return _strip_confidence_score(_tokens()), chunks
