# RAG 챗봇 (FN-CORE-02) 작업 정리

> 브랜치: `feat/rag-chatbot`(머지됨) → `feat/korean-law-mcp-integration`(머지됨) → `fix/precedent-query-mcp-priority`, `feat/category-balanced-retrieval`(머지됨) → `feat/openai-rag-migration`(머지됨), `fix/korean-law-mcp-integration`(머지됨), `fix/mcp-precedent-storytelling`(머지됨), `fix/mcp-off-domain-query-extraction`(머지됨), `tune/answer-page-char-limit`(머지됨)
> 관련 이슈: [FN-CORE-02-rag-chatbot.md](./issue/FN-CORE-02-rag-chatbot.md), [FN-CORE-04-korean-law-mcp.md](./issue/FN-CORE-04-korean-law-mcp.md), [FN-CORE-05-openai-rag-migration.md](./issue/FN-CORE-05-openai-rag-migration.md)
> 관련 문서: [RAG-ARCHITECTURE.md](./RAG-ARCHITECTURE.md)(mermaid 다이어그램), [260805.md](./260805.md)(Ollama 운영 회고), [demo-dialogue.md](./demo-dialogue.md)(시연 대화)
> 최종 수정일: 2026-08-05

## 1. 스코프

내부 문서(설명서/계약서/상속증여세) RAG + 법원판례·법제처 MCP(`korean-law-mcp`) 연동까지 완료. 판례 관련 질의는 내부 DB(상품설명서/계약서엔 판례 원문이 없음) 대신 MCP 실제 판례 데이터를 근거로 사용 — 상세는 4.4절.

이후 `/chat`(프로덕션)을 **OpenAI API(`gpt-4o-mini`)로 전환**하고, 기존 Ollama 버전은
`/prototype/chat`으로 옮겨 그대로 남겨뒀다 — 검색/MCP/DB 로직은 두 경로가 완전히 공유하고
LLM 호출부만 다르다. 배경과 트레이드오프는 6절, 상세 구조는 [RAG-ARCHITECTURE.md](./RAG-ARCHITECTURE.md) 참고.

## 2. 아키텍처

```
사용자 질의
  → bge-m3 임베딩 (packages/rag/embeddings.py)
  → [내부] 카테고리별(설명서/상속증여세/계약서) pgvector 코사인 검색 + 계약서는 은행/신탁유형
    메타데이터 필터 결합 (packages/rag/retriever.py, 기존 HNSW 인덱스 사용) — 판례 질의면 스킵
  → [외부] 판례/법령 키워드 감지 시 korean-law-mcp(search_law/search_decisions) 병렬 호출
    (apps/api/app/mcp_client.py, chat_shared.py) — 판례는 상위 1건 get_decision_text로
    판시사항/판결요지까지 추가 조회(4.4절), 도메인 밖 질의는 키워드 재추출(4.6절)
  → top-1 유사도 < 0.5(내부) & 외부 결과도 없으면 LLM 호출 없이 "자료 없음" 고정 응답
  → 내부 문서 + 외부 판례/법령 컨텍스트 조립 + disclaimer + LLM 스트리밍
    (packages/rag/chains.py — Ollama 기본, openai_chains.py가 ChatOpenAI로 교체해 재사용)
  → 문장 끝 + 800자 이상이면 생성 중단 + "더 설명해드릴까요?" (4.7절)
  → FastAPI SSE로 sources 이벤트 + 토큰 스트림 + done/awaiting_continue 이벤트 전송
    (apps/api/app/chat_shared.py — /chat, /prototype/chat 두 라우터가 공유)
  → chat_sessions/chat_messages/message_sources에 영속화 (source_type: internal_chunk/case_law/statute)
  → apps/web/chat(OpenAI) 또는 prototype/chat(Ollama) 페이지가 fetch+ReadableStream으로
    직접 SSE 파싱해 렌더링
```

### 주요 파일

| 파일 | 역할 |
|---|---|
| `packages/rag/embeddings.py` | bge-m3 쿼리 임베딩 (DB 적재 시 쓴 모델과 동일해야 유사도가 의미 있음) |
| `packages/rag/retriever.py` | 카테고리별 균형 검색(`search_chunks_balanced`) + 은행/신탁유형 메타데이터 필터, `documents` 조인 |
| `packages/rag/chains.py` | 컨텍스트 조립, no-context 임계값 처리, LLM 스트리밍(주입 가능), confidence score 필터링 — 기본 LLM은 Ollama |
| `packages/rag/openai_chains.py` | `chains.py`의 함수를 그대로 호출하되 `ChatOpenAI`만 주입 — 로직 중복 없음 |
| `apps/api/app/chat.py` | `ChatRequest`/`ContinueRequest` 스키마 |
| `apps/api/app/chat_shared.py` | LLM provider 무관 공용 로직 — MCP 라우팅, SSE 페이싱(800자 컷+이어쓰기), DB 저장. `chat_router.py`/`chat_openai_router.py`가 공유 |
| `apps/api/app/routers/chat_router.py` | `POST /chat`, `/chat/continue` — Ollama, `/prototype/chat` 프론트용 |
| `apps/api/app/routers/chat_openai_router.py` | `POST /chat/openai`, `/chat/openai/continue` — OpenAI, `/chat` 프론트(프로덕션)용 |
| `apps/api/app/main.py` | CORS, 기동 시 임베딩모델+Ollama+OpenAI+korean-law-mcp 워밍업 |
| `apps/web/src/app/chat/page.tsx` | 프로덕션 `/chat` — `/chat/openai` 호출 |
| `apps/web/src/app/prototype/chat/page.tsx` | 프로토타입 — 기존 `/chat`(Ollama) 그대로 호출 |
| `apps/api/app/mcp_client.py` | `korean-law-mcp` stdio JSON-RPC 클라이언트, FastAPI 수명 동안 유지되는 단일 프로세스 (search_law/search_decisions/get_decision_text/verify_citations) |
| `packages/rag/test_retriever.py`, `apps/api/tests/test_mcp_client.py` | 회귀 테스트 (아래 4절 참고) |

## 3. 데이터 현황 (Supabase, 실측)

- `documents` 12건 (설명서 4 / 계약서 5 / 상속증여세 3), `chunks` 209건
- 임베딩: `BAAI/bge-m3`, 1024차원, `chunks.embedding`/`chat_messages.embedding` 둘 다 HNSW cosine 인덱스 이미 생성돼 있어 별도 인덱스 작업 불필요

## 4. 정확도 / 품질 실측

### 4.1 Retrieval 설계

- 사용자 질의를 청크와 **동일한 모델(bge-m3, 1024차원)로 임베딩**해 같은 벡터 공간에서 비교 (`packages/rag/embeddings.py`)
- pgvector **코사인 유사도(`<=>`) 기반 검색**으로 209개 청크에서 고속 근사 검색 (기존 HNSW 인덱스 `idx_chunks_embedding` 사용, 별도 인덱스 작업 불필요)
- **단일 검색이 아닌 카테고리별 검색**: 설명서 / 상속증여세 / 계약서 각각 top-k(기본 3)를 따로 조회해 합침(`search_chunks_balanced`) — 단일 전역 top-k면 질의와 가장 가까운 카테고리 하나가 결과를 독식해서 다른 성격의 근거가 밀려나는 문제가 있었음
- **계약서 질의는 메타데이터 필터 결합**: 질의에서 은행명(`detect_bank`)·신탁 유형(`detect_contract_type`)을 감지해 벡터 검색에 `documents.bank`/`documents.contract_type` 조건을 같이 적용 → "하나은행 계약서에서는?" 같은 질문에 정확 대응. `contract_type` 필터는 계약서 카테고리에만 적용(다른 카테고리는 항상 NULL이라 걸면 전멸함), `bank` 필터는 설명서에도 해당 컬럼이 있어 카테고리 무관 적용
- **유사도 임계값(`NO_CONTEXT_THRESHOLD=0.5`) 미달 시 답변하지 않고 질문 구체화 유도** — 근거 없는 답변을 검색 단계에서 차단하는 1차 환각 방지 장치

**임계값 실측 근거**: 설명서/계약서/상속증여세 관련 질의 6개 + 금융이지만 무관한 경계 질의(예: "주식 투자는 어떻게 시작하나요?") 2개 + 완전 무관 질의 2개, 총 11개로 top-1 코사인 유사도 실측:

| 구분 | top-1 유사도 |
|---|---|
| 관련 질의 최소값 | **0.621** |
| 무관/경계 질의 최대값 | **0.442** |

→ 그 사이인 **0.5**를 채택 (양쪽에 여유 마진 확보). `packages/rag/test_retriever.py`가 이 분리를 회귀 테스트로 고정.

**카테고리 분산/메타데이터 필터 실측**: "유언대용신탁을 활용해서 상속세를 줄일 수 있는 방법이 있을까요?" 같은 일반 질의는 설명서/계약서/상속증여세 각 3건씩 정확히 균등하게 잡힘(총 9건). "하나은행 계약서에서는 중도해지 시 어떻게 되나요?"는 `bank="하나은행"` 필터가 걸려 계약서 카테고리 결과 전부가 `하나은행_유언대용신탁계약서.pdf`로만 좁혀지고, top-1(score 0.63)이 정확히 "제18조(중도해지 및 일부해지 등)" 조항으로 잡힘 — 다른 은행 문서가 섞이지 않음을 확인. `packages/rag/test_retriever.py`의 `test_category_balanced`/`test_bank_filter`가 회귀 테스트로 고정.

### 4.2 생성(LLM) — 모델 선정 및 안정성 이슈

**모델**: `hf.co/gchrisoh/EEVE-Korean-Instruct-10.8B-v1.0-Q4_K_M-GGUF` (Ollama)
베이스: `yanolja/EEVE-Korean-Instruct-10.8B-v1.0` (SOLAR-10.7B + 한국어 어휘확장 + DPO), Apache-2.0
- 처음 쓰려던 `hf.co/heegyu/EEVE-Korean-Instruct-10.8B-v1.0-GGUF`는 2024년 초 변환된 구버전 GGUF라 Ollama가 `pull` 시 `"not compatible with llama.cpp"`로 거부 (HF API 확인 결과 `gguf` 메타데이터 자체가 안 잡힘). `gguf-my-repo`로 재변환된 `gchrisoh` 리포로 교체해 해결.
- CPU 전용 서버(EC2 GPU 없음) 전제로 선택 — 상세는 [EC2 배포 계획] 참고.

실측 중 발견해서 고친 문제 3가지:

| 문제 | 원인/증상 | 조치 |
|---|---|---|
| 콜드 스타트 | bge-m3/Ollama가 첫 요청에야 로드 → TTFB 10초+ (요구사항 3초 초과) | FastAPI `lifespan`에서 기동 시 워밍업 + `keep_alive=-1`로 유휴 언로드 방지 → TTFB 1.3~3.6초로 개선 |
| 반복 루프 | 같은 문단을 계속 재생성, 60초+ 응답 안 끝남 | `num_predict=768`(강제 종료 안전망) + `repeat_last_n=256`(문단 단위 반복까지 억제, 기본 64는 못 잡음). `repeat_penalty`는 1.3까지 올렸다가 컨텍스트 인용 자체를 회피하는 회귀가 생겨 1.15로 재조정 |
| 근거 없는 "신뢰도: 90%" | 프롬프트로 금지해도 모델이 무시, 답변 맨 앞/맨 끝 둘 다에서 발생(3/3 실측) | 프롬프트만 믿지 않고 스트림 앞/뒤 ~40자를 지연 버퍼링해 정규식으로 결정적 제거 (`_strip_confidence_score`, 유닛 테스트 포함) |

최종 파라미터(`packages/rag/chains.py`): `repeat_penalty=1.15`, `repeat_last_n=256`, `num_predict=768`, `keep_alive=-1`, `temperature=0.2`. 같은 질의로 4연속 실측해 반복 루프 재발 없음 + 컨텍스트 인용 유지(문서명/조항 정확히 인용, 유류분 같은 법적 예외까지 언급) 확인.

이런 튜닝에도 10.8B 양자화 모델은 지시 준수가 근본적으로 불완전했음(시스템 프롬프트를
스스로 읊거나 질문을 그대로 반복하는 서두, 중간에 삽입되는 "신뢰도: N%" 등 — 실측
재현됨). 이게 6절 OpenAI 전환의 실질적 동기가 됐고, 이 섹션의 내용은 `/prototype/chat`
(Ollama)에 여전히 그대로 적용됨.

### 4.3 korean-law-mcp 연동 (FN-CORE-04)

법원판례/법제처 API를 직접 연동하는 대신 오픈소스 MCP 서버 [korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp)를 stdio JSON-RPC로 호출(`apps/api/app/mcp_client.py`). `LAW_OC=inheritors`가 실제 동작하는 공유 법제처 API 키임을 실측 확인(신탁법/유류분반환 판례 검색 등 실데이터 응답).

**검색어 실측 보정**: 자연어 질문을 그대로 넘기면 거의 항상 0건 (법제처 API가 공백구분 키워드를 AND로 처리 — "유언대용신탁과 유류분" 같은 압축 표현도 실패, "신탁 유류분"처럼 기본 법률용어로 쪼개야 매칭됨). `search_law`(법령명 검색)와 `search_decisions`(판례 전문검색)도 서로 다른 전략 필요 — 전자는 첫 매칭 키워드 하나만, 후자는 여러 키워드 AND가 오히려 정확도를 높임.

**연동이 계속 조용히 실패하던 버그 2개 발견/수정**: 처음엔 판례/법령 검색이 항상
타임아웃 폴백만 반환했음. 원인은 (1) `korean-law-mcp` npm 패키지가 애초에 전역 설치가
안 돼 있었고, (2) `_resolve_script_path()`의 `subprocess.run(["npm","root","-g"], shell=True)`가
POSIX에서 `shell=True`+리스트 인자를 같이 쓰면 셸이 첫 인자(`npm`)만 명령으로 실행하고
나머지(`root`, `-g`)는 버려서 스크립트 경로를 항상 못 찾음(실측 확인). 두 버그 다 고친 뒤
실제 법제처 데이터가 정상적으로 나오는 것 확인.

**호출마다 새 프로세스 spawn하던 구조 → 단일 프로세스로 전환**: korean-law-mcp는
pdfjs/onnxruntime/sharp 등 무거운 의존성 때문에 콜드 기동에만 1~2초 걸림(실측) — 매
호출마다 새로 spawn+kill하면 이 비용을 계속 물어서 라우터의 3초 타임아웃에 걸릴 위험이
있었음. `mcp_client.py`가 FastAPI 수명 동안 프로세스 하나를 유지(`start()`/`aclose()`,
`main.py` lifespan)하도록 바꿔 웜 호출은 1~2초 내로 단축.

### 4.4 판례 질의는 내부 DB 대신 MCP 우선 사용

내부 DB(신탁 상품설명서/계약서)엔 판례 원문이 없어서, 판례 관련 질의를 던지면 "유류분" 같은 단어가 겹치는 상품 안내 문구가 실제 판례 대신 컨텍스트에 섞여 들어가는 문제가 있었음. 판례 키워드(`판례`/`사건`/`판결`/`대법원`/`지방법원`)가 감지되면 내부 벡터 검색 자체를 스킵(`chains.stream_answer`의 `skip_internal`)하고 MCP 결과만 근거로 사용하도록 분리. 신탁 상품/법령 일반 질의는 기존대로 내부 문서 계속 사용 — 회귀 없음 확인.

**판례 설명을 사건번호 나열 대신 스토리텔링으로**: `search_decisions`가 반환하는 건
사건번호/법원/선고일 같은 검색 결과 "목록"일 뿐 판결 이유 자체가 없어서, LLM이 판례를
설명할 때 서지사항만 나열하고 "왜 그렇게 판결났는지"는 설명하지 못했음. 최상위 1건의
사건 id로 `get_decision_text`(판시사항/판결요지 조회)를 추가 호출해 실제 판단 이유까지
컨텍스트에 넣고, 시스템 프롬프트에도 사건번호 나열 대신 시니어가 이해하기 쉬운 말로 짧은
이야기하듯 설명하라는 지시를 추가.

### 4.5 알려진 한계

- 생성 파라미터 튜닝은 특정 질의 셋 기준 실측이라, 실사용 질의 분포가 달라지면 반복/근거회피 재발 가능성 있음 — 재튜닝 시 반드시 동일 질의 3~4회 반복 테스트 필요 (1회 테스트로는 회귀가 안 걸러짐, 실제로 이번에도 그렇게 놓쳤다가 다시 잡음). **OpenAI(`gpt-4o-mini`)로 전환한 `/chat`에서는 이 문제가 실측상 재현되지 않음.**
- `NO_CONTEXT_THRESHOLD=0.5`는 11개 질의 표본 기준 — 실제 사용자 질의 로그가 쌓이면 재조정 필요.
- 은행명/신탁유형 감지(`detect_bank`/`detect_contract_type`)는 이 코퍼스의 distinct 값(은행 6종, 신탁유형 2종) 기준 curated 매핑 — 완전한 NER이 아니라서 새 은행/유형이 추가되면 코드에도 추가해야 함. **추가로 실측된 버그**: 이미 특정 은행 얘기를 하던 중 "OO은행 말고 다른 은행도"처럼 질문에 그 은행명이 다시 언급되면, "다른 은행" 의도와 무관하게 그 은행으로 필터가 고정돼 다른 은행 정보를 "제공할 수 없다"고 오답하는 경우 확인([demo-dialogue.md](./demo-dialogue.md) 하단 참고) — 아직 미수정.
- `korean-law-mcp` 버전이 자주 업데이트됨 (실측 시점 기준 4.9.3) — 도구 스키마가 바뀔 수 있어 문제 생기면 `tools/list`로 먼저 실제 스키마 확인할 것.
- 신탁/상속 도메인 밖 판례 질의(예: "부동산 재건축 판례")는 `_LAW_SEARCH_TERMS` 등 고정 어휘 목록에 안 걸려서 검색어가 빗나갈 수 있었음 — `_extract_keywords`(조사 제거 기반 일반 키워드 추출)로 보정했지만 형태소 분석기가 아니라 완벽하진 않음(4.6절).
- 스미싱 패턴 감지 등 예외 처리(이슈 원문 스코프)는 아직 미구현.

### 4.6 도메인 밖 판례 질의에서 MCP 검색어가 무의미해지는 문제

"부동산 관련 판례 재건축에 대해서 설명해줘" 같은, 신탁/상속 도메인 밖 질의에서
`_build_mcp_query`가 `_PRECEDENT_SEARCH_TERMS` 중 "판례"(판례 여부 분류용 보조어일 뿐
검색 주제가 아님)만 매칭시켜 MCP에 "판례"라는 단어 하나만 넘어가는 문제를 실측으로
발견 — 무관한 검색 결과만 나오거나 "관련 자료를 찾지 못했다"고 오답. 실제 도메인 단어
(신탁/상속/증여 등)가 하나도 안 걸리면 조사·군더더기를 뗀 일반 키워드 추출
(`_extract_keywords`)로 재시도하도록 수정 — "부동산 재건축"으로 재시도하니 실제 관련
판례(재건축 종부세 판례)가 정확히 검색됨. 형태소 분석기 없이 정규식으로 흔한 조사만
떼는 수준이라 완벽하지 않음 — 계속 빗나가면 KoNLPy 등 형태소 분석기 도입 검토.

### 4.7 답변 페이싱 — 문장 끝에서 끊고 이어쓰기

답변을 한 번에 다 쏟아내면 채팅창에서 읽기 피로도가 크다는 피드백으로, 문장이 끝나는
시점(마침표)에 800자 이상이면 **LLM 생성 자체를 중단**(`for` 루프를 `break`)하고
`"더 설명해드릴까요?"`를 붙인 뒤 `event: awaiting_continue`를 보낸다. 뒤에 남은 긴
인용 블록까지 기다리지 않아 응답이 빨리 끝남. `POST /chat/openai/continue`(또는
`/chat/continue`)가 재검색 없이 `message_sources`에 저장된 근거를 재사용하고, 이전
답변을 `AIMessage`로 대화 맥락에 넣어 자연스럽게 이어쓰게 한다. 컷 기준은 처음
400자로 시작했다가, 한 턴에 보이는 답변이 맥락을 다 못 담는다는 피드백으로 800자로
상향 — 여전히 감으로 정한 값.

### 4.8 판례 검색 폴백 — lexguard-mcp (SeoNaRu, Streamable HTTP)

korean-law-mcp가 검색어/rate limit 문제로 판례 0건을 반환할 때, 별개의 국가법령정보센터 API
키로 동작하는 [lexguard-mcp](https://github.com/SeoNaRu/lexguard-mcp)(`precedent_lookup_tool`)를
보조로 호출한다 (`apps/api/app/lexguard_client.py`, `mcp_agent.select_and_run`). 법령
검색(`search_law`)은 폴백 대상에서 제외 — lexguard-mcp엔 동일한 키워드 검색 tool이 없고
(`law_article_tool`은 법령명을 정확히 알아야 하는 직접 조회용), `legal_qa_tool`은 응답
구조가 완전히 달라(법령/판례/해석/위원회 통합 요약, `results` 필드가 평평한 목록이 아님)
파싱을 새로 설계해야 함 — 판례 폴백 하나로 범위를 좁혔다.

**전송 방식이 달라 기존 클라이언트 재사용 불가**: korean-law-mcp는 stdio(자식 프로세스
JSON-RPC)지만 lexguard-mcp는 Streamable HTTP(SSE, `mcp` 공식 SDK 필요) — `mcp_client.py`의
수기 JSON-RPC 코드를 못 쓰고 새 클라이언트를 만들었다. 호출 빈도가 낮은 보조 경로라
korean-law-mcp처럼 프로세스를 상주시키지 않고 매 호출마다 세션을 새로 연다.

**mcp SDK 응답 속성명 실측**: `CallToolResult`는 MCP 스펙상 `isError`/`structuredContent`
(camelCase)지만, 파이썬 클라이언트 객체의 실제 속성은 `is_error`/`structured_content`
(snake_case) — 타입 힌트만 보고 짐작하면 `AttributeError`. 실제 컨테이너를 로컬에 띄우고
더미 키로 호출해 실측 확인.

**precedent_lookup_tool 응답 필드**: `precedents` 배열의 각 항목이 영문 별칭(`case_name`,
`court_name` 등)과 법제처 원본 한글 키(`사건명`, `법원명` 등)를 소스에 따라 섞어 반환해서
(lexguard-mcp 소스의 `src/routes/resource_handlers.py` 실측 확인) 클라이언트가 둘 다
방어적으로 조회.

**LAW_API_KEY는 korean-law-mcp의 LAW_OC와 별개**: open.law.go.kr에서 개별 발급해야 하고
(회원가입 → OPEN API 활용 신청 → **호출하는 서버의 IP/도메인 등록 필요**), 등록한 IP에서만
동작한다 — 로컬 Docker(내 PC IP)와 EC2 배포 환경은 등록을 따로 해야 할 수 있음.

**로컬 실행**: `infra/docker-compose.yml`의 `lexguard-mcp` 서비스가 이 저장소를 벤더링하지
않고 Docker의 git remote build context(`build: context: https://github.com/...`)로 직접
빌드한다 — 서브모듈/코드 복사 없이 최신 upstream을 그대로 씀 (`docker build <git-url>`이
공식 지원하는 기능, 실측 확인).

## 5. 진행 상황 체크리스트

- [x] 질의 embedding + `chunks` 벡터 검색 리트리버 (카테고리별 균형 검색 + 은행/신탁유형 메타데이터 필터)
- [x] LLM 프롬프트 구성 + SSE 스트리밍 응답 API
- [x] `chat_messages`/`message_sources` 기록 로직 (internal_chunk/case_law/statute)
- [x] 출처 카드용 SSE `sources` 이벤트 + 프론트 연동 (`/chat`, 실사용 경로로 승격)
- [x] no-context 임계값 기반 폴백 (할루시네이션 방지 1차 대응)
- [x] 로컬 Ollama 설치 + 모델 pull + end-to-end 실측 검증
- [x] MCP 병렬 호출 (korean-law-mcp: search_law/search_decisions) — FN-CORE-04
- [x] 판례 질의는 내부 DB 대신 MCP 우선 사용
- [x] korean-law-mcp 실연동 버그 수정(npm 미설치, subprocess shell=True) + 단일 프로세스 전환
- [x] 판례 설명 스토리텔링화(`get_decision_text`) + 도메인 밖 질의 키워드 재추출
- [x] 답변 페이싱(문장 끝 컷 + 이어쓰기, `/chat/continue`)
- [x] EC2 배포용 Ollama Docker 이미지 (`popopododo/inheritors-ollama`, GPU 백엔드 제거로 경량화) + nginx 리버스 프록시
- [x] `/chat`을 OpenAI API로 전환, 기존 Ollama는 `/prototype/chat`으로 유지 — FN-CORE-05
- [ ] MCP 타임아웃 폴백 캐싱, 스미싱 감지 예외 처리
- [ ] "OO은행 말고 다른 은행도" 같은 질의에서 `detect_bank`가 필터를 잘못 고정하는 버그 (4.5절)

## 6. OpenAI API 전환 (FN-CORE-05)

`/chat`(프로덕션)의 LLM을 Ollama에서 OpenAI API(`gpt-4o-mini`)로 교체하고, 기존 Ollama
버전은 `/prototype/chat`으로 옮겨 그대로 남겨뒀다. 검색/MCP/DB 로직(`chat_shared.py`,
`retriever.py`, `mcp_client.py`)은 두 경로가 완전히 공유하고, `packages/rag/chains.py`의
`stream_answer`/`continue_answer`가 `llm` 인자를 받도록 파라미터화해서
`openai_chains.py`가 `ChatOpenAI`만 주입해 그대로 재사용한다(로직 중복 없음). 구조는
[RAG-ARCHITECTURE.md](./RAG-ARCHITECTURE.md), 배경/트레이드오프(비용·데이터 프라이버시·
재현성 등)는 [260805.md](./260805.md) 참고.

## 7. 다음 할 일

1. **MCP 캐싱**: 동일 판례/조문 재조회 방지 캐시 (이슈 원문 스코프, 아직 미착수). 폴백은
   판례 검색만 구현됨(4.8절, lexguard-mcp) — 법령 검색 폴백, 캐싱은 아직.
2. **스미싱 패턴 감지**: 답변 생성 중단 + 경고 레이어 (이슈 원문 스코프, 아직 미착수).
3. **은행 필터 오탐 수정**: "KB 말고 다른 은행도" 같은 질의에서 `detect_bank`가 여전히
   해당 은행으로 필터를 고정시키는 문제 (4.5절, [demo-dialogue.md](./demo-dialogue.md) 참고).
4. **`/prototype/chat`(Ollama) EC2 재배포 검증**: 현재 후보 인스턴스(t4g.nano, RAM 0.5GB)는
   모델(6.5GB)을 못 올림 — 더 큰 인스턴스로 사이징 재검토 필요 ([260805.md](./260805.md) 참고).
