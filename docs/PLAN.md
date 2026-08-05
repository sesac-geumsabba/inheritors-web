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
- `/chat` 라우터의 `ERR_INCOMPLETE_CHUNKED_ENCODING` 버그 수정 — LLM 스트리밍 중 예외가 나도
  안내 메시지로 스트림을 정상 종료하도록 처리 (FN-CORE-02)
- 답변을 문장 단위로 끊고 "더 설명해드릴까요?"로 이어 보여주는 페이싱 기능 — 문장이 끝나는
  지점에서 LLM 생성 자체를 중단해 대기시간 단축, `POST /chat/continue`로 원래 근거를
  재검색 없이 재사용해 LangChain 대화 맥락(AIMessage)으로 이어쓰기 (FN-CORE-02)
- 법률/세무 자문이 아님을 알리는 고지 문구를 답변마다 표시 (FN-CORE-02)
- 은행명 줄임 표기(`KB`/`IBK`) 검색 필터 버그 수정 — 리트리버가 풀네임만 인식해 타행 문서가
  섞여 나오던 문제 (FN-CORE-02)
- **korean-law-mcp 실제 연동** — npm 패키지 미설치 + `subprocess.run(shell=True)` POSIX
  버그로 판례/법령 검색이 항상 조용히 실패하던 문제의 근본 원인 확인 후 수정. 호출마다
  새 프로세스를 spawn하던 구조를 FastAPI 수명 동안 유지되는 단일 프로세스로 전환(`main.py`
  lifespan에서 시작/종료). `/chat`에 "판례"/"대법원" 등 키워드가 있으면 MCP 검색 결과가
  `sources`와 Main LLM 컨텍스트(`[법령/판례]`)에 실제로 반영되는 것까지 end-to-end 확인
  (FN-CORE-04)
- **EC2 배포용 Ollama Docker 이미지**: 답변 생성 모델(EEVE-Korean 10.8B Q4, ~6.5GB)을
  이미지에 미리 구워 넣어 컴퓨터마다 재다운로드 불필요하게 함(`infra/ollama/Dockerfile`),
  Docker Hub(`popopododo/inheritors-ollama`)에 push. CPU 전용 배포 대상(AWS Graviton/t4g
  등)에는 안 쓰는 CUDA/Jetpack GPU 백엔드(~3.5GB)를 멀티스테이지 빌드로 제거해
  10.7GB → 6.67GB로 경량화. `infra/nginx/ollama.conf`(스트리밍 대응 프록시 설정)와
  `infra/docker-compose.yml`(컨테이너 네트워크 연결, 포트 루프백 바인딩) 작성
- PR: [#18](https://github.com/sesac-geumsabba/inheritors-web/pull/18)(답변 페이싱/이어쓰기 +
  Ollama Docker), [#19](https://github.com/sesac-geumsabba/inheritors-web/pull/19)(korean-law-mcp
  수정) — `staging` 대상, 리뷰/머지 전

### 다음 단계 (미착수)

- 스미싱 감지 예외 처리 (FN-CORE-02 원 스펙)
- EC2 실제 배포 및 검증 — 현재 후보 인스턴스(t4g.nano, RAM 0.5GB)는 모델(6.5GB)을 못 올려서
  Ollama는 더 큰 인스턴스(최소 8GB+ RAM 권장)에 올리고 API 서버만 t4g.nano에 두는 등
  인스턴스 사이징 재검토 필요
- 답변 자체의 품질 이슈: 10.8B 양자화 모델이 가끔 시스템 프롬프트를 스스로 읊거나 질문을
  반복하는 서두를 붙임(지시 준수 불완전) — 프롬프트 보정으로 완화했으나 완전 해결은 아님
