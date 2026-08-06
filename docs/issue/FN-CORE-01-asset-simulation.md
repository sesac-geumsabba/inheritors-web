---
name: 기능 요청
title: "[FEATURE] FN-CORE-01 3단계 자산승계 시뮬레이션 및 맞춤형 리포트 생성"
labels: feat
---

제안 브랜치명: `feat/asset-simulation`

## 요청 유형

- [x] 새로운 기능 추가

## 어떤 기능인가요?

자산(부동산/예금/주식) + 특약(생전/사후/조건부)을 3단계로 선택하면, 예상 승계 구조·적용 법률·세무 리스크를 정리한 리포트를 생성한다.

- 자산 유형: `APARTMENT` | `COMMERCIAL` | `DEPOSIT` | `STOCK`
- 자산 가액대: `RANGE_UNDER_5B` | `RANGE_5B_10B` | `RANGE_OVER_10B`
- 승계 특약: `LIVING_INCOME` | `DIVIDED_PAY` | `CONDITIONAL_PAY`

## 이 기능이 필요한 이유는 무엇인가요?

사용자가 본인 상황에 맞는 신탁 특약 조합의 법적/세무적 함의를 스스로 파악하기 어려움 — 선택만으로 참고용 리포트를 즉시 받아보게 해 PB 상담 전 단계의 이해를 돕는다.

## 구현 방안

**Backend**
- 자산×특약 조합 → 적용 법률(신탁법 제59조 등)·유류분/상속세 체크포인트 매핑하는 룰 테이블/함수 (DB 테이블 아닌 정적 config로 충분, 조합 수가 작음)
- `POST /api/simulations`: 입력 검증 → 룰 엔진 실행 → `simulations` 테이블에 `assets`/`riders`/`report`(JSONB) 저장, 결과 반환
- 리포트 JSON에 "참고용 정보" 고지 문구 필수 포함

**Frontend**
- 3단계 선택 위저드 UI, 각 단계 미완료 시 다음 단계 진행 차단
- 결과 리포트 카드 컴포넌트 (2초 이내 렌더링)
- 예외 UI: 필수값 누락 시 입력 폼 하이라이팅 + 툴팁, 백엔드 연산 실패 시 안내 메시지 + 재시도 버튼

**DB** (기존 스키마 재사용, 추가 마이그레이션 불필요)
- `simulations(user_id, assets, riders, report, created_at)` — `db/schema.sql`에 이미 정의됨

## 작업 상세 내용

- [ ] 자산×특약 룰 매핑 정의 (법률/세무 체크포인트)
- [ ] `POST /api/simulations` API 구현
- [ ] 3단계 시뮬레이션 위저드 UI
- [ ] 리포트 카드 컴포넌트
- [ ] 입력 누락/연산 실패 예외 처리
- [ ] `simulations` 저장 및 조회 확인

## 완료 기준

3단계 선택 완료 후 2초 이내 리포트 카드가 정상 출력된다.

## 참고할만한 자료

- `docs/PLAN.md`, `db/schema.sql` (`simulations` 테이블)
