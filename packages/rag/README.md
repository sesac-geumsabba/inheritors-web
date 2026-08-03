# packages/rag

LangChain 기반 RAG 로직. 사용자 질의 임베딩 → pgvector 검색 → `packages/legal-mcp` 호출 →
`chains.py`에서 disclaimer + 신탁 자료 + 판례/법령 원문을 조립해 LLM 프롬프트에 주입.

세부 구현은 `feat/rag-citation-injection` 등 개별 기능 브랜치에서 진행.
