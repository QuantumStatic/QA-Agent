from fastapi import FastAPI
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware


configure_logging()

app = FastAPI(title="QA-Agent")
app.add_middleware(RequestIdMiddleware)


@app.get("/api/health")
def health():
    return {"status": "ok"}
