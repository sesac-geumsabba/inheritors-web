# 아키텍처

> 상세 설계(RAG 흐름, 판례 최신성 검증 로직, Docker 배포)는 [유언대용신탁_챗봇_아키텍처.md](./유언대용신탁_챗봇_아키텍처.md) 참고.
> 협업 방식은 [AGENT.md](./AGENT.md), 브랜치/커밋 전략은 [GIT.md](./GIT.md) 참고.
> 최종 수정일: 2026-08-04

## 0. 로컬 실행 사전 준비 (Prerequisites)

`apps/api`(FastAPI)를 띄우려면 아래가 먼저 준비돼야 한다. (`apps/web`만 볼 때는 API 서버 없이도 `npm run dev`는 뜨지만 챗봇 응답은 되지 않는다.)

| 항목 | 필요한 이유 | 확인 |
|---|---|---|
| Node.js 20+, npm | `apps/web` (Next.js) | `node -v`, `npm -v` |
| Python 3.11+ | `apps/api` (FastAPI) | `python3 --version` |
| PostgreSQL + pgvector 확장 | `chat_messages.embedding` 등 벡터 컬럼 저장/검색 (`apps/api/app/db.py`, `packages/rag/retriever.py`) | `DATABASE_URL`이 가리키는 DB에 `CREATE EXTENSION IF NOT EXISTS vector;` 필요 (Supabase는 기본 제공) |
| Ollama + 모델 pull | 챗봇 답변 생성 LLM (`packages/rag/chains.py`) | 아래 참고 |

### Ollama 설치 및 모델 준비

```bash
# 1. 설치 (macOS)
brew install ollama
# 또는 https://ollama.com/download 에서 설치

# 2. 서버 기동 — 백그라운드로 계속 떠 있어야 /chat이 동작한다
ollama serve

# 3. 답변 생성 모델 pull (기본값, OLLAMA_MODEL로 다른 모델 지정 가능) — 약 6.5GB, 시간 걸림
ollama pull hf.co/gchrisoh/EEVE-Korean-Instruct-10.8B-v1.0-Q4_K_M-GGUF
```

- `OLLAMA_BASE_URL`(기본 `http://localhost:11434`)과 `OLLAMA_MODEL`은 `apps/api/.env`에서 바꿀 수 있다 (`.env.example` 참고).
- 모델을 pull하지 않은 채 `/chat`을 호출하면 스트림이 중간에 끊기고 브라우저 콘솔에 `ERR_INCOMPLETE_CHUNKED_ENCODING`이 뜬다.
- 질의 임베딩 모델(`BAAI/bge-m3`, `packages/rag/embeddings.py`)은 별도 설치가 필요 없다 — 첫 요청 시 Hugging Face Hub에서 자동 다운로드된다(수 GB, 인터넷 필요). Rate limit이 걸리면 `HF_TOKEN` 환경변수를 추가한다.

### (대안) 로컬 설치 대신 Docker로 — 컴퓨터마다 모델을 새로 받지 않으려면

`ollama pull`은 6.5GB라 컴퓨터마다 반복하면 느리다. 모델을 이미지에 미리 구워 Docker Hub에
올려둔 `popopododo/inheritors-ollama`를 pull만 해서 쓰면 이 과정이 필요 없다 (`infra/ollama/Dockerfile`).

```bash
docker run -d --name ollama -p 11434:11434 -v ollama_models:/root/.ollama popopododo/inheritors-ollama:latest
```

- 이 컨테이너를 다른 서버에 올려두면, 각자 컴퓨터의 `apps/api/.env`에서 `OLLAMA_BASE_URL`을
  그 서버 주소(`http://<서버 IP>:11434`)로만 바꾸면 로컬에 Ollama/모델 없이도 `/chat`이 된다.
- `infra/docker-compose.yml`로 web+api+ollama를 한 번에 띄우면 `OLLAMA_BASE_URL`은
  compose가 컨테이너 네트워크용(`http://ollama:11434`)으로 자동 설정한다.
- 이미지는 빌드한 컴퓨터의 아키텍처(현재 arm64)로만 올라가 있다 — x86 서버에 배포하려면
  `docker buildx build --platform linux/amd64 ...`로 다시 빌드해 push해야 한다.
- 다른 모델로 바꾸려면 `infra/ollama/Dockerfile`의 `MODEL` ARG를 바꿔 재빌드 후 push.

## 1. 모노레포 구성

npm workspaces + Turborepo 기반 모노레포.

```
inheritors-web/
├── apps/
│   ├── web/            # Next.js 14 (App Router) 프론트엔드
│   └── api/             # FastAPI 백엔드
├── packages/
│   ├── rag/             # LangChain RAG 체인
│   ├── legal-mcp/       # 법원/법제처 API 연동 클라이언트
│   └── shared-types/    # FE/BE 공유 타입
├── infra/
│   ├── docker-compose.yml
│   └── nginx/
├── docs/
└── turbo.json
```

- 루트 `package.json`의 `workspaces`가 `apps/*`, `packages/*`를 묶고, `npm run dev` / `npm run build`는 `turbo run dev` / `turbo run build`로 위임된다 (`turbo.json`).
- `apps/api`가 `packages/rag`, `packages/legal-mcp`를 import하므로 API를 Docker로 빌드할 때 빌드 컨텍스트는 프로젝트 루트여야 한다 (`apps/api/Dockerfile` 참고).

## 2. 컴포넌트별 현재 상태

| 위치 | 역할 | 현재 상태 |
|---|---|---|
| `apps/web` | Next.js 프론트엔드 | 기본 App Router 스캐폴드만 존재 (`src/app/layout.tsx`, `page.tsx`) |
| `apps/api` | FastAPI 백엔드 | `/health`, `/health/db` 두 엔드포인트만 구현 (`app/main.py`, `app/db.py`) |
| `packages/rag` | LangChain RAG 체인 | `chains.py`는 TODO 스텁 |
| `packages/legal-mcp/clients` | 법원/법제처 API 클라이언트 | `court_precedent.py`, `moleg_statute.py` 모두 TODO 스텁 (인증 방식/rate limit 미확정) |
| `packages/shared-types` | FE/BE 공유 타입 | 빈 모듈 (`export {}`) |

즉 현재는 모노레포 골격 + DB 연결 확인용 헬스체크만 있는 초기 단계이며, RAG/법률 API 연동/신탁 도메인 로직은 아직 구현되지 않았다. 새 기능을 추가할 때는 위 표의 위치에 맞춰 채워 넣는다.

## 3. 기술 스택

- **Frontend**: Next.js 14, React 18, TypeScript (`apps/web/package.json`)
- **Backend**: FastAPI, SQLAlchemy 2, Pydantic 2, psycopg2 (`apps/api/requirements.txt`)
- **DB**: PostgreSQL 단일 인스턴스(Supabase 등), `DATABASE_URL` 환경변수로 연결 (`apps/api/app/db.py`)
- **RAG**: LangChain 기반, `packages/rag`에서 `packages/legal-mcp`를 호출하는 구조로 설계됨
- **Infra**: Docker (`apps/web/Dockerfile`, `apps/api/Dockerfile`), `infra/docker-compose.yml`로 web+api 통합 구동

## 4. 환경변수

- `apps/api/.env`: `DATABASE_URL`, `COURT_PRECEDENT_API_KEY`, `MOLEG_STATUTE_API_KEY`
- `apps/web/.env`: `NEXT_PUBLIC_API_BASE_URL`

새 환경변수 추가 시 `.env.example`도 함께 갱신한다 ([AGENT.md](./AGENT.md) 참고).

## 5. 요청 흐름 (목표 설계)

```
Next.js(apps/web) → FastAPI(apps/api) → packages/rag → packages/legal-mcp → 법원/법제처 API
```

프론트는 `NEXT_PUBLIC_API_BASE_URL`로 FastAPI를 직접 호출하고, FastAPI가 RAG 체인 및 법률 API 연동을 담당한다. 별도 서버 분리 없이 FastAPI 프로세스 안에서 외부 API 콜을 처리하는 이유와 판례 최신성 검증 로직은 [유언대용신탁_챗봇_아키텍처.md](./유언대용신탁_챗봇_아키텍처.md#3-rag-아키텍처-흐름)에 상세히 있다.

## 6. 작업 시 참고

- 브랜치 전략, 커밋 컨벤션, rebase 절차: [GIT.md](./GIT.md)
- ISSUE/PR 작성, FE/BE 분리 작업 원칙, 코드 리뷰 규칙: [AGENT.md](./AGENT.md)
