# RAG 챗봇 (FN-CORE-02) 작업 정리

> 브랜치: `feat/rag-chatbot`(머지됨) → 이후 `feat/korean-law-mcp-integration`(머지됨), `fix/precedent-query-mcp-priority`, `feat/category-balanced-retrieval`
> 관련 이슈: [FN-CORE-02-rag-chatbot.md](./issue/FN-CORE-02-rag-chatbot.md), [FN-CORE-04-korean-law-mcp.md](./issue/FN-CORE-04-korean-law-mcp.md)
> 최종 수정일: 2026-08-05

## 1. 스코프

내부 문서(설명서/계약서/상속증여세) RAG + 법원판례·법제처 MCP(`korean-law-mcp`) 연동까지 완료. 판례 관련 질의는 내부 DB(상품설명서/계약서엔 판례 원문이 없음) 대신 MCP 실제 판례 데이터를 근거로 사용 — 상세는 4.4절.

## 2. 아키텍처

```
사용자 질의
  → bge-m3 임베딩 (packages/rag/embeddings.py)
  → [내부] 카테고리별(설명서/상속증여세/계약서) pgvector 코사인 검색 + 계약서는 은행/신탁유형
    메타데이터 필터 결합 (packages/rag/retriever.py, 기존 HNSW 인덱스 사용) — 판례 질의면 스킵
  → [외부] 판례/법령 키워드 감지 시 korean-law-mcp(search_law/search_decisions) 병렬 호출
    (apps/api/app/mcp_client.py, chat_router.py)
  → top-1 유사도 < 0.5(내부) & 외부 결과도 없으면 LLM 호출 없이 "자료 없음" 고정 응답
  → 내부 문서 + 외부 판례/법령 컨텍스트 조립 + disclaimer + Ollama(EEVE-Korean) 스트리밍 (packages/rag/chains.py)
  → FastAPI SSE로 sources 이벤트 + 토큰 스트림 + done 이벤트 전송 (apps/api/app/routers/chat_router.py)
  → chat_sessions/chat_messages/message_sources에 영속화 (source_type: internal_chunk/case_law/statute)
  → apps/web/chat 페이지가 fetch+ReadableStream으로 직접 SSE 파싱해 렌더링
```

### 주요 파일

| 파일 | 역할 |
|---|---|
| `packages/rag/embeddings.py` | bge-m3 쿼리 임베딩 (DB 적재 시 쓴 모델과 동일해야 유사도가 의미 있음) |
| `packages/rag/retriever.py` | 카테고리별 균형 검색(`search_chunks_balanced`) + 은행/신탁유형 메타데이터 필터, `documents` 조인 |
| `packages/rag/chains.py` | 컨텍스트 조립, no-context 임계값 처리, Ollama 스트리밍, confidence score 필터링 |
| `apps/api/app/chat.py` | `ChatRequest` 스키마 |
| `apps/api/app/routers/chat_router.py` | `POST /chat` SSE 라우터, 세션/메시지/출처 저장 |
| `apps/api/app/main.py` | CORS, 기동 시 임베딩모델+Ollama 워밍업 |
| `apps/web/src/app/chat/page.tsx` | 실제 입력창 + SSE 스트리밍 렌더링 (프로토타입 목업에서 교체, 실사용 경로로 승격) |
| `apps/api/app/mcp_client.py` | `korean-law-mcp` stdio JSON-RPC 클라이언트 (search_law/search_decisions/verify_citations) |
| `packages/rag/test_retriever.py`, `test_chains.py` | 회귀 테스트 (아래 4절 참고) |

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

### 4.3 korean-law-mcp 연동 (FN-CORE-04)

법원판례/법제처 API를 직접 연동하는 대신 오픈소스 MCP 서버 [korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp)를 stdio JSON-RPC로 호출(`apps/api/app/mcp_client.py`). `LAW_OC=inheritors`가 실제 동작하는 공유 법제처 API 키임을 실측 확인(신탁법/유류분반환 판례 검색 등 실데이터 응답).

**검색어 실측 보정**: 자연어 질문을 그대로 넘기면 거의 항상 0건 (법제처 API가 공백구분 키워드를 AND로 처리 — "유언대용신탁과 유류분" 같은 압축 표현도 실패, "신탁 유류분"처럼 기본 법률용어로 쪼개야 매칭됨). `search_law`(법령명 검색)와 `search_decisions`(판례 전문검색)도 서로 다른 전략 필요 — 전자는 첫 매칭 키워드 하나만, 후자는 여러 키워드 AND가 오히려 정확도를 높임.

### 4.4 판례 질의는 내부 DB 대신 MCP 우선 사용

내부 DB(신탁 상품설명서/계약서)엔 판례 원문이 없어서, 판례 관련 질의를 던지면 "유류분" 같은 단어가 겹치는 상품 안내 문구가 실제 판례 대신 컨텍스트에 섞여 들어가는 문제가 있었음. 판례 키워드(`판례`/`사건`/`판결`/`대법원`/`지방법원`)가 감지되면 내부 벡터 검색 자체를 스킵(`chains.stream_answer`의 `skip_internal`)하고 MCP 결과만 근거로 사용하도록 분리. 신탁 상품/법령 일반 질의는 기존대로 내부 문서 계속 사용 — 회귀 없음 확인.

### 4.5 알려진 한계

- 생성 파라미터 튜닝은 특정 질의 셋 기준 실측이라, 실사용 질의 분포가 달라지면 반복/근거회피 재발 가능성 있음 — 재튜닝 시 반드시 동일 질의 3~4회 반복 테스트 필요 (1회 테스트로는 회귀가 안 걸러짐, 실제로 이번에도 그렇게 놓쳤다가 다시 잡음).
- `NO_CONTEXT_THRESHOLD=0.5`는 11개 질의 표본 기준 — 실제 사용자 질의 로그가 쌓이면 재조정 필요.
- 은행명/신탁유형 감지(`detect_bank`/`detect_contract_type`)는 이 코퍼스의 distinct 값(은행 6종, 신탁유형 2종) 기준 curated 매핑 — 완전한 NER이 아니라서 새 은행/유형이 추가되면 코드에도 추가해야 함.
- `korean-law-mcp` 버전이 자주 업데이트됨 (실측 시점 기준 4.9.3, 2일 전 릴리즈) — 도구 스키마가 바뀔 수 있어 문제 생기면 `tools/list`로 먼저 실제 스키마 확인할 것.
- 스미싱 패턴 감지 등 예외 처리(이슈 원문 스코프)는 아직 미구현.

## 5. 진행 상황 체크리스트

- [x] 질의 embedding + `chunks` 벡터 검색 리트리버 (카테고리별 균형 검색 + 은행/신탁유형 메타데이터 필터)
- [x] LLM 프롬프트 구성 + SSE 스트리밍 응답 API
- [x] `chat_messages`/`message_sources` 기록 로직 (internal_chunk/case_law/statute)
- [x] 출처 카드용 SSE `sources` 이벤트 + 프론트 연동 (`/chat`, 실사용 경로로 승격)
- [x] no-context 임계값 기반 폴백 (할루시네이션 방지 1차 대응)
- [x] 로컬 Ollama 설치 + 모델 pull + end-to-end 실측 검증
- [x] MCP 병렬 호출 (korean-law-mcp: search_law/search_decisions) — FN-CORE-04
- [x] 판례 질의는 내부 DB 대신 MCP 우선 사용
- [ ] MCP 타임아웃 폴백 캐싱, 스미싱 감지 예외 처리
- [ ] EC2 배포용 Dockerfile (Ollama+모델 이미지, ECR push)

## 6. 다음 할 일

1. **EC2 배포**: 로컬에서 Ollama+모델을 Docker 이미지로 구워(`ollama serve &` → `ollama pull`) ECR에 push, EC2는 `docker pull`만 하도록 구성. Docker Hub 대신 ECR인 이유는 같은 리전 pull 속도 + rate limit 회피 + private repo 사실상 무료. 권장 인스턴스: `m6i.xlarge`(4vCPU/16GB, 논버스터블), EBS 30GB.
2. **MCP 캐싱/폴백**: 동일 판례/조문 재조회 방지 캐시, 타임아웃 시 폴백 데이터 (이슈 원문 스코프, 아직 미착수).
3. **스미싱 패턴 감지**: 답변 생성 중단 + 경고 레이어 (이슈 원문 스코프, 아직 미착수).
