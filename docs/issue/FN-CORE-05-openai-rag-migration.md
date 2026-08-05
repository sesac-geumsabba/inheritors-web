---
name: 기능 요청
title: "[FEATURE] FN-CORE-05 /chat OpenAI API 전환 — /prototype/chat에 기존 Ollama 유지"
labels: feat
---

제안 브랜치명: `feat/openai-rag-migration`

## 요청 유형

- [x] 새로운 기능 추가

## 어떤 기능인가요?

현재 `/chat`이 쓰는 로컬 Ollama(EEVE-Korean 10.8B) LLM 연동을 OpenAI API(GPT 모델) 연동으로
교체한다. 기존 Ollama 연동은 버리지 않고 `/prototype/chat`(신규 라우트)으로 옮겨 그대로
남겨둔다 — `/prototype/start`, `/prototype/report`처럼 프로토타입 데모 플로우의 일부로 유지.

- `/prototype/chat` → 기존 Ollama 기반 챗봇 (변경 없음, 그대로 이동)
- `/chat` → 신규 OpenAI API 기반 RAG 챗봇 (검색/MCP 로직은 동일, LLM만 교체)

## 이 기능이 필요한 이유는 무엇인가요?

이번 세션에서 Ollama를 EC2에 배포하며 겪은 문제들(모델 6.5GB 다운로드, RAM 부족으로
OOM, GPU 백엔드 죽은 용량 등 — `docs/PLAN.md` 참고)이 운영 부담으로 확인됨. OpenAI API로
전환하면 서버에 모델을 직접 띄울 필요가 없어져 인스턴스 사이징 문제가 사라지고, 응답
품질도(10.8B 양자화 모델의 지시 준수 불완전 문제 등) 개선될 여지가 있다. 다만 완전히
갈아엎기 전에 기존 Ollama 버전을 프로토타입으로 남겨 비교/롤백 여지를 둔다.

## 구현 방안

**Backend**
- `packages/rag/chains.py`의 `stream_answer`/`continue_answer`가 이미 `_build_messages`로
  프롬프트를 조립하고 마지막에만 `_llm().stream(messages)`를 호출하는 구조라, LLM 인스턴스를
  주입받도록 파라미터화(`llm` 인자 추가, 기본값은 기존 Ollama)해서 로직 중복 없이 재사용
- `packages/rag/openai_chains.py` 신설: `ChatOpenAI`(langchain-openai)로 LLM만 교체해
  `chains.stream_answer`/`continue_answer`를 그대로 호출
- 판례/법령 검색(MCP), 은행/문서 검색(retriever), DB 저장 로직은 LLM과 무관하므로
  `chat_router.py`의 재사용 가능한 부분(`_event_stream`, `_fetch_external_sources`,
  `_load_context_for_continue`, `_save_message` 등)을 공용 모듈로 분리해 두 라우터가 공유
- 새 라우터 `POST /chat/openai`, `POST /chat/openai/continue` 추가 (기존 `/chat`,
  `/chat/continue`는 그대로 유지 — `/prototype/chat` 프론트가 계속 호출)
- `requirements.txt`에 `langchain-openai` 추가, `.env`에 `OPENAI_API_KEY`/`OPENAI_MODEL` 추가

**Frontend**
- `apps/web/src/app/prototype/chat/`: 기존 `apps/web/src/app/chat/`의 페이지를 그대로 복사해
  이동 (Ollama 백엔드 `/chat`, `/chat/continue` 호출 유지)
- `apps/web/src/app/chat/page.tsx`: 새 백엔드 `/chat/openai`, `/chat/openai/continue` 호출로 교체
- `prototype/start` 페이지의 "시작하기" CTA를 `/prototype/chat`으로 변경 (프로토타입 플로우
  자체 완결성 유지). `BottomNavBar`의 "상담소" 탭은 `/chat` 그대로 (신규 프로덕션 경로)

**DB**
- 스키마 변경 없음 — `chat_messages`/`message_sources`는 provider와 무관하게 공유

## 작업 상세 내용

- [ ] `OPENAI_API_KEY` 발급 및 `.env` 반영 (사용자가 직접 등록)
- [ ] `langchain-openai` 설치, `packages/rag/openai_chains.py` 작성
- [ ] `chains.py`의 `stream_answer`/`continue_answer`에 `llm` 주입 파라미터 추가
- [ ] `chat_router.py`의 공용 헬퍼를 공유 모듈로 분리, `chat_openai_router.py` 신설
- [ ] 프론트 `/prototype/chat` 신설(기존 페이지 이동), `/chat`은 신규 백엔드로 교체
- [ ] `prototype/start` CTA 링크 `/prototype/chat`으로 변경
- [ ] 두 경로 모두 실호출 테스트 (판례/법령 MCP, 은행 필터, 이어쓰기 플로우 포함)

## 완료 기준

`/prototype/chat`은 기존과 동일하게 Ollama로 답변하고, `/chat`은 OpenAI API로 답변하며,
둘 다 동일한 검색/MCP/저장 로직(사실상 LLM 호출부만 다름)을 공유한다.

## 참고할만한 자료

- [FN-CORE-02-rag-chatbot.md](./FN-CORE-02-rag-chatbot.md), [FN-CORE-04-korean-law-mcp.md](./FN-CORE-04-korean-law-mcp.md)
- `docs/PLAN.md` (Ollama EC2 배포 중 겪은 문제 기록)
