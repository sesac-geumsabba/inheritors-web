# RAG 챗봇 (FN-CORE-02) 작업 정리

> 브랜치: `feat/rag-chatbot` (staging에서 분기, 아직 PR 안 올림)
> 관련 이슈: [FN-CORE-02-rag-chatbot.md](./issue/FN-CORE-02-rag-chatbot.md)
> 최종 수정일: 2026-08-05

## 1. 스코프

1차는 **내부 문서(설명서/계약서/상속증여세) 기반 RAG만**. 법원판례·법제처 MCP 연동(FN-CORE-04)은 인증 방식 미확정 상태라 의도적으로 후순위로 미룸 — `message_sources.source_type` enum에 `case_law`/`statute` 값이 이미 준비돼 있어서 나중에 붙여도 스키마 변경 없이 확장 가능.

## 2. 아키텍처

```
사용자 질의
  → bge-m3 임베딩 (packages/rag/embeddings.py)
  → pgvector 코사인 검색: chunks.embedding <=> 질의벡터 (packages/rag/retriever.py, 기존 HNSW 인덱스 사용)
  → top-1 유사도 < 0.5 면 LLM 호출 없이 "자료 없음" 고정 응답
  → 컨텍스트 조립 + disclaimer + Ollama(EEVE-Korean) 스트리밍 (packages/rag/chains.py)
  → FastAPI SSE로 sources 이벤트 + 토큰 스트림 + done 이벤트 전송 (apps/api/app/routers/chat_router.py)
  → chat_sessions/chat_messages/message_sources에 영속화
  → apps/web/prototype/chat 페이지가 fetch+ReadableStream으로 직접 SSE 파싱해 렌더링
```

### 주요 파일

| 파일 | 역할 |
|---|---|
| `packages/rag/embeddings.py` | bge-m3 쿼리 임베딩 (DB 적재 시 쓴 모델과 동일해야 유사도가 의미 있음) |
| `packages/rag/retriever.py` | `chunks` 코사인 검색, `documents` 조인해 메타데이터 포함 |
| `packages/rag/chains.py` | 컨텍스트 조립, no-context 임계값 처리, Ollama 스트리밍, confidence score 필터링 |
| `apps/api/app/chat.py` | `ChatRequest` 스키마 |
| `apps/api/app/routers/chat_router.py` | `POST /chat` SSE 라우터, 세션/메시지/출처 저장 |
| `apps/api/app/main.py` | CORS, 기동 시 임베딩모델+Ollama 워밍업 |
| `apps/web/src/app/prototype/chat/page.tsx` | 실제 입력창 + SSE 스트리밍 렌더링 (정적 목업에서 교체) |
| `packages/rag/test_retriever.py`, `test_chains.py` | 회귀 테스트 (아래 4절 참고) |

## 3. 데이터 현황 (Supabase, 실측)

- `documents` 12건 (설명서 4 / 계약서 5 / 상속증여세 3), `chunks` 209건
- 임베딩: `BAAI/bge-m3`, 1024차원, `chunks.embedding`/`chat_messages.embedding` 둘 다 HNSW cosine 인덱스 이미 생성돼 있어 별도 인덱스 작업 불필요

## 4. 정확도 / 품질 실측

### 4.1 검색(리트리버) — no-context 임계값 보정

설명서/계약서/상속증여세 관련 질의 6개 + 금융이지만 무관한 경계 질의(예: "주식 투자는 어떻게 시작하나요?") 2개 + 완전 무관 질의 2개, 총 11개로 top-1 코사인 유사도 실측:

| 구분 | top-1 유사도 |
|---|---|
| 관련 질의 최소값 | **0.621** |
| 무관/경계 질의 최대값 | **0.442** |

→ 그 사이인 **0.5**를 `NO_CONTEXT_THRESHOLD`로 채택 (양쪽에 여유 마진 확보). `packages/rag/test_retriever.py`가 이 분리를 회귀 테스트로 고정.

top-5까지의 점수 하락도 완만함을 확인 (예: 0.700 → 0.657) — 노이즈 섞인 하위권 청크가 컨텍스트에 끼어드는 문제는 없어서 별도 재랭킹/필터링 추가 안 함.

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

### 4.3 알려진 한계

- 생성 파라미터 튜닝은 특정 질의 셋 기준 실측이라, 실사용 질의 분포가 달라지면 반복/근거회피 재발 가능성 있음 — 재튜닝 시 반드시 동일 질의 3~4회 반복 테스트 필요 (1회 테스트로는 회귀가 안 걸러짐, 실제로 이번에도 그렇게 놓쳤다가 다시 잡음).
- `NO_CONTEXT_THRESHOLD=0.5`는 11개 질의 표본 기준 — 실제 사용자 질의 로그가 쌓이면 재조정 필요.
- 스미싱 패턴 감지 등 예외 처리(이슈 원문 스코프)는 아직 미구현.

## 5. 진행 상황 체크리스트

- [x] 질의 embedding + `chunks` 벡터 검색 리트리버
- [x] LLM 프롬프트 구성 + SSE 스트리밍 응답 API
- [x] `chat_messages`/`message_sources` 기록 로직
- [x] 출처 카드용 SSE `sources` 이벤트 + 프론트 연동 (`/prototype/chat`)
- [x] no-context 임계값 기반 폴백 (할루시네이션 방지 1차 대응)
- [x] 로컬 Ollama 설치 + 모델 pull + end-to-end 실측 검증
- [ ] MCP 병렬 호출 (법원 판례 API, 법제처 API) — FN-CORE-04, 별도 스코프
- [ ] MCP 타임아웃 폴백, 스미싱 감지 예외 처리
- [ ] EC2 배포용 Dockerfile (Ollama+모델 이미지, ECR push)
- [ ] `feat/rag-chatbot` → `staging` PR

## 6. 다음 할 일

1. **EC2 배포**: 로컬에서 Ollama+모델을 Docker 이미지로 구워(`ollama serve &` → `ollama pull`) ECR에 push, EC2는 `docker pull`만 하도록 구성. Docker Hub 대신 ECR인 이유는 같은 리전 pull 속도 + rate limit 회피 + private repo 사실상 무료. 권장 인스턴스: `m6i.xlarge`(4vCPU/16GB, 논버스터블), EBS 30GB.
2. **PR**: 지금까지 커밋(`feat/rag-chatbot`, 8개 커밋) staging 대상 PR로 올리기.
3. **MCP 연동**: 법원판례/법제처 API 인증 방식 확정되면 FN-CORE-04로 별도 착수.
