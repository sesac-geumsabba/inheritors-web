from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers.chat_router import router as chat_router
from app.routers.quick_buttons_router import router as quick_buttons_router
from packages.rag.chains import warm_up
from packages.rag.embeddings import embed_query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 첫 실사용자가 bge-m3/Ollama 콜드 로드를 겪지 않도록 기동 시 미리 로딩.
    # 둘 다 로컬 dev에서 아직 준비 안 됐을 수 있어 실패해도 서버는 계속 기동.
    try:
        embed_query("warmup")
    except Exception as e:
        print(f"[warn] 임베딩 모델 warm-up 실패: {e}")
    try:
        warm_up()
    except Exception as e:
        print(f"[warn] Ollama warm-up 실패, 첫 /chat 요청이 콜드 로드될 수 있음: {e}")
    yield


app = FastAPI(title="유언대용신탁 자산승계 설계 챗봇 API", lifespan=lifespan)

app.include_router(quick_buttons_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

