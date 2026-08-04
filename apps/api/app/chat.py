from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: int | None = None
    message: str
