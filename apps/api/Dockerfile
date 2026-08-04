FROM python:3.11-slim AS base
WORKDIR /app

# 빌드 컨텍스트는 리포 루트 (infra/docker-compose.yml 참고) — packages/rag를 import하므로 필요.
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ .
COPY packages/ ./packages/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
