---
name: 기능 요청
title: "[FEATURE] FN-CORE-04 korean-law-mcp 연동 — 판례/법령 질의 시 MCP 호출"
labels: feat
---

제안 브랜치명: `feat/korean-law-mcp-integration`

## 요청 유형

- [x] 새로운 기능 추가

## 어떤 기능인가요?

RAG 챗봇(FN-CORE-02)에서 판례·법령 관련 질의가 들어오면, 자체 법원/법제처 API 연동을 새로 만드는 대신 오픈소스 MCP 서버 [korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp)를 호출해 응답을 생성한다.

## 이 기능이 필요한 이유는 무엇인가요?

FN-CORE-02 스펙상 "법원도서관 판례 API + 법제처 API" 병렬 호출이 필요한데, `korean-law-mcp`가 법제처 Open API 42개를 10개 도구(법령·판례·행정규칙·자치법규·조약·해석례 검색 + **LLM 인용 환각 검증**)로 이미 감싸둔 검증된 서버라 직접 API 연동보다 개발 비용이 훨씬 낮고, `verify_citations`로 답변의 판례/조문 인용이 실존하는지까지 자동 검증할 수 있다.

## 구현 방안

**설치/설정**
- 로컬 설치: `npm install -g korean-law-mcp` (Node.js 18+ 필요)
- 법제처 Open API 인증키(OC) 무료 발급 후 `LAW_OC` 환경변수로 전달 → `inheritors-RAG/.env`에 추가 (이미 `.gitignore` 처리됨)
- MCP 실행 방식은 stdio(`command: korean-law-mcp`) 로컬 프로세스로 백엔드에 붙임 (원격 HTTP 방식(`mcp.gomdori.app`)은 외부 트래픽 의존이라 자체 서버 배포 시 로컬 설치 우선 고려)

**Backend**
- 챗봇 질의 라우팅에서 판례/법령 관련 질의로 분류되면 MCP 클라이언트로 아래 도구 호출
  - `search_law` / `search_decisions`: 법령·판례 검색
  - `get_precedent_text`: 판례 본문 조회
  - `legal_research`: 복합 리서치가 필요한 질의(HyDE 확장된 질의 등)
  - `verify_citations`: LLM이 생성한 답변의 인용 조문/판례 실존 여부 최종 검증 (환각 방지 게이트)
- 검색 결과를 FN-CORE-02의 `message_sources`에 매핑 저장 (`source_type = 'case_law' | 'statute'`, `title`/`url`/`snippet`)
- 예외 처리는 FN-CORE-02와 동일하게 MCP 응답 3초 초과 시 캐시 폴백

**DB**
- 스키마 변경 없음 — 기존 `message_sources.source_type`(`case_law`/`statute`)이 이미 이 용도로 설계돼 있음

## 작업 상세 내용

- [ ] 법제처 Open API 인증키(OC) 발급, `.env`에 `LAW_OC` 추가
- [ ] `korean-law-mcp` 로컬 설치 및 백엔드 프로세스로 기동
- [ ] MCP 클라이언트 연동 (stdio 통신)
- [ ] 질의 라우팅: 판례/법령 질의 감지 → `search_law`/`search_decisions`/`legal_research` 호출
- [ ] 검색 결과 → `message_sources` 저장 로직
- [ ] 답변 생성 후 `verify_citations`로 인용 검증 (선택, 권장)
- [ ] 타임아웃/폴백 처리 (FN-CORE-02와 공유)

## 완료 기준

판례/법령 관련 질의 시 `korean-law-mcp`가 호출되어, 법제처 실데이터 기반 출처(사건번호/조문)가 답변과 출처 카드에 포함된다.

## 참고할만한 자료

- https://github.com/chrisryugj/korean-law-mcp
- [FN-CORE-02-rag-chatbot.md](./FN-CORE-02-rag-chatbot.md)
