from fastapi import FastAPI
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.auth.routes import router as auth_router


configure_logging()

app = FastAPI(title="QA-Agent")
app.add_middleware(RequestIdMiddleware)
app.include_router(auth_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
