---
name: 기능 요청
title: "[FEATURE] FN-CORE-02 MCP 기반 법률/판례 RAG 대화형 챗봇"
labels: feat
---

제안 브랜치명: `feat/rag-chatbot`

## 요청 유형

- [x] 새로운 기능 추가

## 어떤 기능인가요?

상속/신탁 관련 구어체 질문에 대해 MCP로 법원도서관 판례 API + 법제처 API를 병렬 조회하고, 그 컨텍스트만으로 LLM이 SSE 스트리밍 답변 + 출처 카드를 생성한다.

## 이 기능이 필요한 이유는 무엇인가요?

법률 용어에 익숙하지 않은 사용자가 일상어로 질문해도 판례·법령 근거가 명확한 답변을 받게 해 신뢰도를 높이고 상담 전환으로 연결한다.

## 구현 방안

**Backend**
- 질의 embedding(`BAAI/bge-m3`) 계산 → `chunks.embedding`에 대해 pgvector `<=>` 코사인 유사도 검색 (내부 RAG 문서: 설명서/계약서/상속증여세)
- MCP 병렬 호출: 법원도서관 판례 API, 법제처 API (HyDE/Query Expansion으로 검색어 확장 후 호출)
- 내부 검색 결과 + 외부 API 결과를 합쳐 LLM 프롬프트 구성, SSE로 스트리밍 응답
- `chat_messages`에 질의(embedding 포함)/답변 저장, `message_sources`에 인용 출처 저장 (`source_type`: `internal_chunk`는 `chunk_id` FK, `case_law`/`statute`는 `title`/`url`/`snippet`; `score`/`rank`에 검색 시점 유사도·순위 기록)
- 예외: MCP 외부 API 3초 초과 시 캐시된 판례 데이터로 폴백, 스미싱/사기 패턴 감지 시 답변 생성 중단 + 경고 레이어

**Frontend**
- 페르소나(`SENIOR`|`JUNIOR`)별 질의 입력 UI, SSE 스트리밍 답변 렌더링
- 판례 사건번호/신탁법 조문 출처 카드 (Document 링크 포함)
- 금감원 스미싱 경고 레이어 UI

**DB** (기존 스키마 재사용)
- `chat_sessions`, `chat_messages`(role/content/embedding), `message_sources`(source_type/chunk_id/score/rank) — `db/schema.sql`에 이미 정의됨
- 새로 필요: MCP 폴백용 캐시 저장소 — 캐시 히트율 등 실측 후 필요하면 별도 테이블/Redis 검토 (지금은 스코프 아님)

## 작업 상세 내용

- [ ] 질의 embedding + `chunks` 벡터 검색 리트리버 구현
- [ ] MCP 병렬 호출 (법원 판례 API, 법제처 API) 연동
- [ ] LLM 프롬프트 구성 + SSE 스트리밍 응답 API
- [ ] `chat_messages`/`message_sources` 기록 로직
- [ ] 출처 카드 UI
- [ ] MCP 타임아웃 폴백, 스미싱 감지 예외 처리

## 완료 기준

질의 후 3초 이내 스트리밍 답변 시작, 인용 판례 근거가 명시되어 출력된다.

## 참고할만한 자료

- `docs/PLAN.md`, `db/schema.sql` (`chat_sessions`/`chat_messages`/`message_sources`/`chunks`), `load_to_db.py`
