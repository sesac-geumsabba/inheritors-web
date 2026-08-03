# 협업 가이드

브랜치 전략은 [GIT.md](./GIT.md) 참고.

## 작업 원칙

- 작업 시 작은 단위로 TASK를 나누고 체크리스트로 관리할 것.
- 작업 시 해당 기능에 대한 ISSUE를 먼저 작성하고, 그 ISSUE에 연결되도록 PR을 작업할 것.
- 프론트엔드/백엔드 작업은 각각 ISSUE를 생성하고, `front`/`back` 라벨을 달아 작업한다.
- 다른 coworker와의 git 충돌을 피하기 위해 같은 파일을 동시에 수정하는 것을 최대한 지양한다.
- 모든 코드 수정은 `staging`에서 `feat/{개발할 기능}` 브랜치를 파서 작업한다.
- 작업 내용은 ISSUE 및 PR로 남기고, `.github/ISSUE_TEMPLATE/` 하위 템플릿 또는 `PULL_REQUEST_TEMPLATE.md`를 참고해 항목에 맞게 상세히 작성한다.

## Frontend

- 기능별로 프로젝트 구조를 나눠서 작업한다 (페이지별로 폴더 구조를 새로 구성).

## Backend

- 기존 `/` context path 외의 API도 별도 `.py` 파일로 분리하여 작업한다.

브랜치 네이밍 / 커밋 메시지 컨벤션은 [GIT.md](./GIT.md) 참고.

## 코드 리뷰 & 머지

- PR은 최소 1인 이상의 approve 후 merge한다.
- merge 방식은 **squash merge**로 통일해 `staging` 커밋 히스토리를 깔끔하게 유지한다.
- 리뷰어는 본인이 작성한 PR을 스스로 approve/merge하지 않는다.

## 환경변수 / 시크릿 관리

- `.env`는 절대 커밋하지 않는다 (`.gitignore`에 이미 등록됨).
- 새 환경변수가 추가되면 `.env.example`도 함께 갱신해 PR에 포함한다.
- API 키, DB 접속정보 등 민감 정보는 PR 설명이나 커밋 메시지에 남기지 않는다.

## 작업 전 체크

- 작업 시작 전 관련 ISSUE가 없다면 먼저 생성한다.
- 로컬에서 lint/build/테스트를 통과하는지 확인한 뒤 PR을 올린다.
