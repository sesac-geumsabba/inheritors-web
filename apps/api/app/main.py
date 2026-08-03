from fastapi import FastAPI

app = FastAPI(title="유언대용신탁 자산승계 설계 챗봇 API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
