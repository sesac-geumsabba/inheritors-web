---
name: 기능 요청
title: "[FEATURE] FN-CORE-03 챗봇 기능별 Quick 버튼(판례/사례/신탁) 연동"
labels: feat
---

제안 브랜치명: `feat/chatbot-quick-buttons`

## 요청 유형

- [x] 새로운 기능 추가

## 어떤 기능인가요?

입력이 서툰 사용자를 위해 Quick 버튼(`BTN_PRECEDENT`|`BTN_CASES`|`BTN_TRUST_TYPES`) 클릭만으로 대표 판례/실생활 사례/신탁 특약 종류를 프리셋 질문으로 즉시 조회한다.

## 이 기능이 필요한 이유는 무엇인가요?

타이핑에 익숙하지 않은 5060 시니어 사용자의 챗봇 진입 장벽을 낮춘다.

## 구현 방안

**Backend**
- 버튼 클릭을 FN-CORE-02 챗봇 플로우의 프리셋 질의로 매핑해 재사용 (`BTN_PRECEDENT` → 유류분/유언대용신탁 대표 판례 3건 등)
- 카테고리별 프리셋 콘텐츠(대표 판례, 사례, 특약 설명)는 `documents`/`chunks`에 미리 적재해두고 조회 (새 테이블 불필요)

**Frontend**
- Quick 버튼 UI, 클릭 시 프리셋 질문을 챗봇 입력으로 전송
- Document 응답 지연 시 스켈레톤 로더

**DB**
- 별도 테이블 없음 — FN-CORE-02의 `chat_messages`/`message_sources` 그대로 사용

## 작업 상세 내용

- [ ] Quick 버튼 UI (판례/사례/신탁 3종)
- [ ] 버튼별 프리셋 질의 → 챗봇 플로우 연동
- [ ] 카테고리별 프리셋 콘텐츠 확인 (기존 `chunks` 데이터로 충분한지 점검, 부족하면 추가 크롤링)
- [ ] 스켈레톤 로더

## 완료 기준

버튼 클릭 즉시 대화창에 프리셋 질문 전송 및 추천 Document 카드가 노출된다.

## 참고할만한 자료

- [FN-CORE-02-rag-chatbot.md](./FN-CORE-02-rag-chatbot.md), `db/schema.sql`
