# Git 브랜치 전략

## 브랜치 구조

```
main
 └─ staging
     └─ feat/{기능명}
```

- `main`: 배포 기준 브랜치. 직접 push/PR 금지.
- `staging`: 개발 통합 브랜치. 모든 `feat/` 브랜치는 여기서 분기하고 여기로 합친다.
- `feat/{기능명}`: 기능 단위 작업 브랜치. `staging`에서 분기.

## 브랜치 네이밍

- 목적에 따라 prefix를 구분한다: `feat/{기능명}`, `fix/{버그명}`, `docs/{문서명}`, `chore/{작업명}`
- 기능명은 영문 kebab-case로 간결하게 작성한다 (예: `feat/trust-contract-crud`)

## 커밋 메시지 컨벤션

- `type: 작업 내용` 형식으로 작성한다.
- type: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`
- 예: `feat: 신탁 계약 조회 API 추가`

## 규칙

1. **main에는 push, PR을 하지 않는다.** 모든 작업은 `staging`을 거친다.
2. **브랜치는 기능별로 생성**하여 작업한다. 하나의 브랜치에 여러 기능을 섞지 않는다.
3. **PR은 staging으로**, 작업 커밋들을 모아 한 번에 올린다. (`feat/{기능명}` → `staging`)
4. **작업 시작 전 rebase**: `staging`에서 새 브랜치를 파기 전에 반드시 최신 `staging`을 pull 받아 최신 상태로 작업을 시작한다.

```bash
git checkout staging
git pull origin staging
git checkout -b feat/{기능명}
```

## PR 전 체크

- 커밋을 기능 단위로 정리했는지 확인
- `staging` 기준 최신화(rebase)했는지 확인
- PR 대상 브랜치가 `staging`인지 확인 (`main` 아님)
