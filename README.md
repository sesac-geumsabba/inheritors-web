# 유언대용신탁 자산승계 설계 챗봇

시니어 자산가 대상 유언대용신탁 특약/세금 안내 + 법률 판례 RAG 챗봇

브랜치 전략 및 아키텍처: docs/유언대용신탁_챗봇_아키텍처.md

## 시작하기

### 1. 클론

```bash
git clone git@github.com:sesac-geumsabba/inheritors-web.git
cd inheritors-web
```

### 2. Web (apps/web)

```bash
npm install          # 루트에서 실행 (workspaces로 apps/*, packages/* 함께 설치)
cp apps/web/.env.example apps/web/.env
npm run dev          # turbo run dev -> apps/web에서 next dev
```

### 3. API (apps/api)

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate      # macOS/Linux는 source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # DATABASE_URL 등 값 채우기
uvicorn app.main:app --reload
```

- 서버: http://127.0.0.1:8000
- DB 연결 확인: http://127.0.0.1:8000/health/db
