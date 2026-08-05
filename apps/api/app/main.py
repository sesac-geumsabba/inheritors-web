from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.mcp_client import mcp_client
from app.routers.chat_router import router as chat_router
from app.routers.mcp_router import router as mcp_router
from packages.rag.chains import warm_up
from packages.rag.embeddings import embed_query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 첫 실사용자가 bge-m3/Ollama 콜드 로드를 겪지 않도록 기동 시 미리 로딩.
    # 셋 다 로컬 dev에서 아직 준비 안 됐을 수 있어 실패해도 서버는 계속 기동.
    try:
        embed_query("warmup")
    except Exception as e:
        print(f"[warn] 임베딩 모델 warm-up 실패: {e}")
    try:
        warm_up()
    except Exception as e:
        print(f"[warn] Ollama warm-up 실패, 첫 /chat 요청이 콜드 로드될 수 있음: {e}")
    try:
        # korean-law-mcp는 콜드 기동에 1~2초 걸려서(pdfjs/onnxruntime/sharp 등 무거운 require)
        # 미리 띄워두지 않으면 첫 판례/법령 질문이 라우터 타임아웃에 걸릴 수 있음.
        await mcp_client.start()
    except Exception as e:
        print(f"[warn] korean-law-mcp 기동 실패, 판례/법령 검색이 안 될 수 있음: {e}")
    yield
    await mcp_client.aclose()


app = FastAPI(title="유언대용신탁 자산승계 설계 챗봇 API", lifespan=lifespan)

# ponytail: 로컬 프로토타입 테스트용으로 넓게 허용. 실배포 시 NEXT_PUBLIC_API_BASE_URL에
# 대응하는 실제 프론트 도메인으로 좁혀야 함.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mcp_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
