FROM python:3.11-slim AS builder
WORKDIR /app

# 빌드 컨텍스트는 리포 루트 (infra/docker-compose.yml 참고) — packages/rag를 import하므로 필요.
# --prefix=/install: 최종 스테이지로 site-packages만 옮기고 pip/setuptools/wheel 자체나
# 빌드 중간 산물은 최종 이미지에 남기지 않는다. requirements.txt가 안 바뀌면 이 레이어는
# BuildKit 캐시(build-images.yml의 cache-from/to)로 통째로 스킵된다 — sentence-transformers가
# 끌고오는 torch 재다운로드가 실제 빌드 시간을 좌우해서, 캐시 적중이 곧 속도.
COPY apps/api/requirements.txt .
# --extra-index-url: sentence-transformers가 끌고오는 torch가 기본 PyPI 인덱스로는 CUDA용
# nvidia-* 패키지까지 같이 깔린다(실측: GPU 없는 arm64 서버인데 5GB+로 부풀어 오름) — PyTorch가
# 공식 제공하는 CPU 전용 인덱스를 추가로 걸어서 torch만 CPU 빌드로 받게 한다.
RUN pip install --no-cache-dir --prefix=/install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /install /usr/local

# tests/, .env* 등은 .dockerignore로도 걸러지지만, app/과 packages/만 명시적으로 골라
# 담아서 실행에 안 쓰는 파일이 애초에 이미지에 들어올 여지를 없앤다.
COPY apps/api/app ./app
COPY packages/ ./packages/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
