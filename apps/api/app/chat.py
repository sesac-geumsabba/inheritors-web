from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: int | None = None
    message: str


class ContinueRequest(BaseModel):
    message_id: int
    continue_count: int = 0
