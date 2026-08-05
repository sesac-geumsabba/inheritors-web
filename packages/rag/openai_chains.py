"""OpenAI(GPT) 기반 답변 생성. 검색/프롬프트 조립/no-context 폴백/신뢰도 문구 제거는
packages/rag/chains.py와 완전히 동일 — LLM 인스턴스만 ChatOpenAI로 바꿔 그대로 넘긴다.
/chat(신규, OpenAI)과 /prototype/chat(기존, Ollama)이 이 두 파일로 갈린다."""

import os
from collections.abc import Iterator
from functools import lru_cache

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from packages.rag import chains
from packages.rag.retriever import PER_CATEGORY_TOP_K, RetrievedChunk


@lru_cache(maxsize=1)
def _llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=0.2,
    )


def warm_up() -> None:
    """서버 기동 시 1회 호출 — API 키가 잘못됐거나 요금 문제가 있으면 여기서 바로 드러남."""
    _llm().invoke("ping")


def stream_answer(
    db: Session,
    query: str,
    query_embedding: list[float],
    per_category_k: int = PER_CATEGORY_TOP_K,
    external_sources: list[dict] | None = None,
    skip_internal: bool = False,
) -> tuple[Iterator[str], list[RetrievedChunk]]:
    return chains.stream_answer(
        db,
        query,
        query_embedding,
        per_category_k=per_category_k,
        external_sources=external_sources,
        skip_internal=skip_internal,
        llm=_llm(),
    )


def continue_answer(
    query: str, previous_answer: str, chunks: list[RetrievedChunk], external_sources: list[dict]
) -> Iterator[str]:
    return chains.continue_answer(query, previous_answer, chunks, external_sources, llm=_llm())
