from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers.chat_router import router as chat_router
from app.routers.quick_buttons_router import router as quick_buttons_router

app = FastAPI(title="유언대용신탁 자산승계 설계 챗봇 API")

app.include_router(quick_buttons_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

