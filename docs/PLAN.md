# PLAN

## 기획 개요

- **서비스명**: 상속자들 (`inheritors-web`)
- **목적**: 5060 시니어 자산가 및 3040 자녀 대상, 유언대용신탁 특약 시뮬레이션 + MCP 기반 실시간 법원 판례 RAG 챗봇 제공 → 상속 분쟁 예방, 은행 PB 대면 상담(O2O) 전환
- **타겟 플랫폼**: PC/모바일 웹 (React / Next.js)
- 이 저장소(`inheritors-RAG`)는 그 중 RAG(법률 판례/세법 검색) 서비스 담당

### MVP 기능 범위

| 구분 | 기능 ID | 기능명 | 비고 |
|---|---|---|---|
| Core | FN-CORE-01 | 3단계 자산승계 시뮬레이션 및 맞춤형 리포트 생성 | `simulations` 테이블 |
| Core | FN-CORE-02 | MCP 기반 법률/판례 RAG 대화형 챗봇 | `chat_sessions`/`chat_messages`/`message_sources` |
| Core | FN-CORE-03 | 챗봇 Quick 버튼(판례/사례/신탁) 연동 | 별도 테이블 없이 위 스키마 재사용 |
| Core | FN-CORE-04 | korean-law-mcp 연동 (판례/법령 질의) | 원 스펙엔 없던 추가 기능, FN-CORE-02 하위 |
| Support | FN-SUPP-01 | 온보딩 모달 | DB 불필요 (클라이언트) |
| Support | FN-SUPP-02 | 시니어 맞춤 폰트 크기 조절 | DB 불필요 (클라이언트) |
| Post | FN-POST-01 | 공시가격 자동 산정 & PDF 다운로드 | 추후 기능, 미구현 |
| Post | FN-POST-02 | 채팅 세션 저장 기능 | `chat_sessions`/`chat_messages` |

### 기능별 개발 이슈

프론트/백엔드 개발은 기능 단위로 나눠 `docs/issue/`에 정리 (브랜치 전략은 `docs/GIT.md`: `feat/{기능명}` → `staging`).

| 기능 ID | 이슈 문서 |
|---|---|
| FN-CORE-01 | [FN-CORE-01-asset-simulation.md](./issue/FN-CORE-01-asset-simulation.md) |
| FN-CORE-02 | [FN-CORE-02-rag-chatbot.md](./issue/FN-CORE-02-rag-chatbot.md) |
| FN-CORE-03 | [FN-CORE-03-quick-buttons.md](./issue/FN-CORE-03-quick-buttons.md) |
| FN-CORE-04 | [FN-CORE-04-korean-law-mcp.md](./issue/FN-CORE-04-korean-law-mcp.md) |
| FN-SUPP-01 | [FN-SUPP-01-onboarding-modal.md](./issue/FN-SUPP-01-onboarding-modal.md) |
| FN-SUPP-02 | [FN-SUPP-02-font-size-control.md](./issue/FN-SUPP-02-font-size-control.md) |
| FN-POST-01/02 | 상세 스펙 미확정, 이슈 미작성 (백로그) |

## 진행 과정

1. **원본 데이터 수집**: `data/` 하위 3개 카테고리(설명서, 계약서, 상속 증여세) PDF 12건 확보
2. **청킹**: PDF를 조항/문단 단위로 파싱해 `data/{설명서,계약서,상속증여세}_chunks.csv` 생성
   - 공통 컬럼: `chunk_id`, `file_name`, `page`, `content`, `n_chars`
   - 카테고리별 추가 컬럼: 계약서(`contract_type`, `bank`, `keyword`), 설명서(`bank`)
3. **DB 스키마 설계** (`db/schema.sql`, PostgreSQL + pgvector)
   - `documents` / `chunks`: RAG 원본 문서·청크 + 임베딩(`VECTOR(1024)`)
   - `users` / `simulations`: FN-CORE-01
   - `chat_sessions` / `chat_messages` / `message_sources`: FN-CORE-02/03, FN-POST-02
   - `chat_messages.embedding`, `message_sources.score/rank`: 질의-문서 관계도 기록용 (추천 로직 근거 데이터)
4. **임베딩 모델**: `BAAI/bge-m3` (다국어, 1024차원, `sentence-transformers`로 로드)
5. **DB 적재** (`load_to_db.py`, Supabase Postgres): `documents` 12건, `chunks` 209건 임베딩 포함 적재 완료

## 진행 상태

기능별 상세 작업은 위 "기능별 개발 이슈" 표의 각 문서 참고. RAG 파이프라인 관련 상세 진행상황·정확도 실측치는 [docs/RAG.md](./RAG.md) 참고.

### 완료

- pgvector `<=>` 코사인 유사도로 `chunks.embedding` 검색하는 리트리버 (FN-CORE-02)
- 검색 결과를 `message_sources`(score/rank 포함)에 기록하는 로직 (FN-CORE-02)
- 내부 문서 기반 RAG 체인 + Ollama(EEVE-Korean) 스트리밍 응답, no-context 임계값 폴백 (FN-CORE-02)
- `feat/rag-chatbot` 브랜치에서 `/prototype/chat` 프론트 연동까지 완료, 로컬 end-to-end 테스트 완료 (아직 staging PR 전)

### 다음 단계 (미착수)

- MCP(법원 판례 API·법제처 API) 연동 및 `source_type='case_law'/'statute'` 케이스 처리 (FN-CORE-04)
- MCP 타임아웃 폴백, 스미싱 감지 예외 처리 (FN-CORE-02 원 스펙)
- EC2 배포용 Ollama+모델 Docker 이미지 빌드 및 ECR 배포 (상세는 [docs/RAG.md](./RAG.md) 6절)
- `feat/rag-chatbot` → `staging` PR
