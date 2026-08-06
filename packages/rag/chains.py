"""disclaimer + 신탁 자료를 조립해 LLM에 주입하는 RAG 체인. 컨텍스트에 없는 내용은 답하지 않도록 강제.

기본 LLM은 Ollama(EEVE-Korean)지만 stream_answer/continue_answer 둘 다 llm 인자로 다른
ChatModel을 주입받을 수 있다 — packages/rag/openai_chains.py가 이 방식으로 검색/프롬프트
조립 로직은 그대로 두고 ChatOpenAI로만 바꿔 재사용한다."""

import os
import re
from collections.abc import Iterator
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session

from packages.rag.retriever import (
    PER_CATEGORY_TOP_K,
    RetrievedChunk,
    detect_bank,
    detect_contract_type,
    search_chunks_balanced,
)

# ponytail: 설명서/계약서/상속증여세 3카테고리 + 경계(금융이지만 무관)/완전무관 질의 11개로 보정.
# 관련 질의 top-1 최소 0.621, 무관·경계 질의 top-1 최대 0.442 — 그 사이 값으로 마진 확보.
# 실제 질의 로그 쌓이면 재조정 필요 (test_retriever.py의 CASES가 회귀 체크 역할).
NO_CONTEXT_THRESHOLD = 0.5
NO_CONTEXT_MESSAGE = (
    "문의하신 내용과 관련된 자료를 찾지 못했습니다. "
    "다른 표현으로 다시 질문해 주시거나 은행 PB 상담을 이용해 주세요."
)

SYSTEM_PROMPT = """당신은 유언대용신탁 상담 챗봇입니다.
아래 [문서]와 [법령/판례]에 있는 내용만 근거로 답변하세요. 거기 없는 내용은 추측하거나 지어내지 말고 모른다고 답하세요.
답변 마지막에 "신뢰도: 90%" 같은 confidence score를 절대 붙이지 마세요. 그런 수치는 근거가 없습니다.
답변은 본 서비스가 법률/세무 자문이 아닌 정보 제공 목적임을 자연스럽게 밝히고, 참고한 문서명/법령명/사건번호를 함께 표시하세요.
인사말이나 위 지침을 스스로 읊는 것으로 답변을 시작하지 말고, 질문을 [질문]처럼 그대로 반복하지도 말고, 바로 답변 내용부터 시작하세요.
[법령/판례]의 판례 내용을 설명할 때는 사건번호·법원명·선고일 같은 서지사항을 나열하지 말고,
"어떤 상황에서 누가 무엇을 다퉜고 법원이 왜 그렇게 판단했는지"를 시니어 이용자가 이해하기 쉬운
말로, 짧은 이야기하듯 풀어서 설명하세요. 사건번호는 나중에 찾아볼 수 있도록 답변 맨 끝에
참고용으로만 짧게 덧붙이세요."""


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


def _build_external_context(sources: list[dict]) -> str:
    label = {"statute": "법령", "case_law": "판례"}
    return "\n\n".join(
        f"[{label.get(s.get('source_type'), '외부자료')}] {s.get('title', '')}\n{s.get('snippet', '')}"
        for s in sources
    )


def _build_messages(
    query: str, chunks: list[RetrievedChunk], external_sources: list[dict]
) -> list[SystemMessage | HumanMessage]:
    context_parts = []
    if chunks:
        context_parts.append("[문서]\n" + _build_context(chunks))
    if external_sources:
        context_parts.append("[법령/판례]\n" + _build_external_context(external_sources))
    return [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{chr(10).join(context_parts)}"),
        HumanMessage(content=query),
    ]


def _stream_tokens(messages: list[BaseMessage], llm: BaseChatModel) -> Iterator[str]:
    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content


def continue_answer(
    query: str,
    previous_answer: str,
    chunks: list[RetrievedChunk],
    external_sources: list[dict],
    llm: BaseChatModel | None = None,
) -> Iterator[str]:
    """"더 설명해드릴까요?"에 사용자가 "네"로 답했을 때 이어 쓰는 답변.

    검색은 다시 하지 않고 원래 답변에 쓰인 근거(chunks/external_sources)를 그대로 재사용하며,
    이전 답변을 대화 맥락(AIMessage)에 넣어 같은 내용을 반복하지 않고 자연스럽게 이어가게 한다.

    llm을 안 주면 기존 Ollama를 그대로 쓴다 — packages/rag/openai_chains.py가 이 함수를
    그대로 호출하면서 ChatOpenAI 인스턴스만 넘겨 검색/프롬프트 조립 로직을 재사용한다.
    """
    messages = [
        *_build_messages(query, chunks, external_sources),
        AIMessage(content=previous_answer),
        HumanMessage(content="네, 이어서 설명해주세요."),
    ]
    return _strip_confidence_score(_stream_tokens(messages, llm or _llm()))


def stream_answer(
    db: Session,
    query: str,
    query_embedding: list[float],
    per_category_k: int = PER_CATEGORY_TOP_K,
    external_sources: list[dict] | None = None,
    skip_internal: bool = False,
    llm: BaseChatModel | None = None,
) -> tuple[Iterator[str], list[RetrievedChunk]]:
    """답변 토큰 스트림과, message_sources 기록용으로 실제 인용된 내부 청크 목록을 함께 반환.

    query_embedding은 호출 측(라우터)이 이미 계산해 chat_messages 저장에도 쓰는 값을 그대로 받는다
    (같은 질의를 두 번 임베딩하지 않기 위해).
    external_sources는 packages/legal-mcp 등에서 가져온 판례/법령 결과
    ({source_type, title, url, snippet, score, rank} dict 리스트, chat_router에서 조립).

    내부 검색은 설명서/상속증여세/계약서 카테고리별로 top-k를 따로 조회해 합친다 — 단일
    전역 top-k면 질의와 제일 가까운 카테고리 하나가 결과를 독식해서 다른 성격의 근거가
    밀려날 수 있음. 계약서 관련 질의는 은행명/신탁유형이 감지되면 벡터 검색에 메타데이터
    필터를 결합해 "하나은행 계약서에서는?" 같은 질문에 정확히 대응한다.

    skip_internal=True면 내부 문서 검색 자체를 안 함 — 순수 판례 질의는 내부 DB(신탁 상품
    설명서/계약서)에 실제 판례 원문이 없어서, 의미상 비슷해 보이는(예: "유류분" 언급) 상품
    안내 문구가 판례 대신 인용되는 오답 유발 가능 (chat_router에서 판단해 전달).

    llm을 안 주면 기존 Ollama를 그대로 쓴다 — packages/rag/openai_chains.py가 이 함수를
    그대로 호출하면서 ChatOpenAI 인스턴스만 넘겨 검색/프롬프트 조립 로직을 재사용한다.
    """
    external_sources = external_sources or []
    if skip_internal:
        chunks: list[RetrievedChunk] = []
    else:
        bank = detect_bank(query)
        contract_type = detect_contract_type(query)
        chunks = search_chunks_balanced(
            db, query_embedding, per_category_k=per_category_k, bank=bank, contract_type=contract_type
        )

    has_internal = bool(chunks) and chunks[0].score >= NO_CONTEXT_THRESHOLD
    if not has_internal and not external_sources:
        return iter([NO_CONTEXT_MESSAGE]), []

    used_chunks = chunks if has_internal else []
    messages = _build_messages(query, used_chunks, external_sources)
    return _strip_confidence_score(_stream_tokens(messages, llm or _llm())), used_chunks
