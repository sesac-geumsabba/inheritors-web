# RAG 챗봇 아키텍처 (2026-08-05 기준)

`/chat`(OpenAI)과 `/prototype/chat`(Ollama) 두 경로가 검색·MCP·DB 로직을 공유하고 LLM
호출부만 갈아끼우는 구조. 관련 문서: [RAG.md](./RAG.md), [260805.md](./260805.md),
[issue/FN-CORE-05-openai-rag-migration.md](./issue/FN-CORE-05-openai-rag-migration.md)

## 전체 구조

```mermaid
flowchart TD
    subgraph FE["apps/web (Next.js)"]
        ChatPage["/chat\n(상담소, 프로덕션)"]
        ProtoPage["/prototype/chat\n(프로토타입)"]
    end

    subgraph API["apps/api (FastAPI)"]
        subgraph Routers["routers/"]
            OpenAIRouter["chat_openai_router.py\nPOST /chat/openai\nPOST /chat/openai/continue"]
            OllamaRouter["chat_router.py\nPOST /chat\nPOST /chat/continue"]
        end

        Shared["chat_shared.py\n(provider 무관 공용 로직)\n- fetch_external_sources (MCP 라우팅)\n- event_stream (SSE, 800자 컷 + 이어쓰기 트리거)\n- save_message / load_context_for_continue"]

        MCPClient["mcp_client.py\nFastAPI 수명 동안 유지되는\nkorean-law-mcp 프로세스\n(search_law / search_decisions / get_decision_text)"]
    end

    subgraph RAG["packages/rag/"]
        OpenAIChains["openai_chains.py\nstream_answer/continue_answer\n(ChatOpenAI 주입)"]
        Chains["chains.py\nstream_answer/continue_answer\n(llm 인자로 교체 가능, 기본 ChatOllama)"]
        Retriever["retriever.py\nsearch_chunks_balanced\n(카테고리별 top-k + 은행/신탁유형 필터)"]
        Embeddings["embeddings.py\nembed_query (BAAI/bge-m3)"]
    end

    subgraph DB["PostgreSQL + pgvector"]
        Docs[("documents / chunks\n(설명서·계약서·상속증여세)")]
        ChatDB[("chat_sessions\nchat_messages\nmessage_sources")]
    end

    subgraph EXT["외부 서비스"]
        OpenAIAPI["OpenAI API\n(gpt-4o-mini)"]
        Ollama["Ollama\n(EEVE-Korean 10.8B, 로컬/EC2)"]
        LawAPI["법제처 Open API /\n법원 판례 (국세법령정보시스템 등)"]
    end

    ChatPage -->|POST| OpenAIRouter
    ProtoPage -->|POST| OllamaRouter

    OpenAIRouter --> Shared
    OllamaRouter --> Shared

    Shared -->|"질의 임베딩"| Embeddings
    Embeddings --> Retriever
    Retriever --> Docs

    Shared -->|"판례/법령 키워드 감지 시"| MCPClient
    MCPClient --> LawAPI

    OpenAIRouter --> OpenAIChains
    OllamaRouter --> Chains
    OpenAIChains -->|"llm=ChatOpenAI로 위임"| Chains
    Chains -->|"검색 결과 + MCP 결과로\n프롬프트 조립 후 스트리밍"| OpenAIAPI
    Chains --> Ollama

    Shared --> ChatDB
```

## 답변 스트리밍 · 이어쓰기 흐름

```mermaid
sequenceDiagram
    participant U as 사용자
    participant FE as chat/page.tsx
    participant R as chat_openai_router.py
    participant S as chat_shared.py
    participant M as mcp_client.py
    participant C as openai_chains.py → chains.py
    participant L as OpenAI API

    U->>FE: 질문 입력
    FE->>R: POST /chat/openai {message}
    R->>S: fetch_external_sources(message)
    S->>M: search_law / search_decisions (판례·법령 키워드 시)
    M-->>S: 법제처 실데이터 (판시사항/판결요지 포함)
    R->>C: stream_answer(query, embedding, external_sources)
    C->>C: retriever.search_chunks_balanced (내부 문서 검색)
    C->>L: 프롬프트(내부 문서 + 법령/판례) 스트리밍 요청
    L-->>R: 토큰 스트림
    R-->>FE: SSE data: 토큰 (실시간)
    Note over R: 문장 끝 + 800자 이상이면<br/>생성 중단, "더 설명해드릴까요?" 추가
    R-->>FE: event: awaiting_continue {message_id}
    R->>S: save_message + message_sources 저장
    R-->>FE: event: done {session_id}

    U->>FE: "네, 더 설명해주세요" 클릭
    FE->>R: POST /chat/openai/continue {message_id}
    R->>S: load_context_for_continue(message_id)
    S-->>R: 원 질문 + 이전 답변 + 저장된 근거 (재검색 없음)
    R->>C: continue_answer(...) — AIMessage로 이전 답변 대화 맥락에 포함
    C->>L: 이어서 생성 요청
    L-->>R: 토큰 스트림
    R-->>FE: SSE 스트림 (동일한 페이싱 로직 재적용)
```

## 두 경로의 차이점 요약

| | `/chat` (프로덕션) | `/prototype/chat` (프로토타입) |
|---|---|---|
| 프론트 | `apps/web/src/app/chat/` | `apps/web/src/app/prototype/chat/` |
| 백엔드 라우터 | `chat_openai_router.py` | `chat_router.py` |
| LLM | OpenAI API (`gpt-4o-mini`) | Ollama (`EEVE-Korean-Instruct-10.8B`, Q4) |
| LLM 위치 | OpenAI 클라우드 | 로컬 또는 EC2 자체 호스팅 |
| 검색/MCP/DB | **완전히 동일** (`chat_shared.py`, `retriever.py`, `mcp_client.py`) | 좌동 |

## 알려진 제약

- Ollama 경로는 셀프호스팅 인스턴스의 RAM이 모델 크기(6.5GB)보다 커야 함 — 자세한 배포
  이력과 한계는 [260805.md](./260805.md) 참고
- korean-law-mcp는 법제처 API를 감싼 것이라 도메인(신탁/상속) 밖 질의는 키워드 추출이
  더 필요할 수 있음 (`chat_shared.py`의 `_extract_keywords`)
