# 아키텍처

> 상세 설계(RAG 흐름, 판례 최신성 검증 로직, Docker 배포)는 [유언대용신탁_챗봇_아키텍처.md](./유언대용신탁_챗봇_아키텍처.md) 참고.
> 협업 방식은 [AGENT.md](./AGENT.md), 브랜치/커밋 전략은 [GIT.md](./GIT.md) 참고.
> 최종 수정일: 2026-08-04

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
