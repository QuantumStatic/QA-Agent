import os
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException

from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.auth.routes import router as auth_router
from app.documents.routes import router as documents_router
from app.conversations.routes import router as conversations_router
from app.deps import get_current_user
from app.auth.models import User as UserModel


configure_logging()

app = FastAPI(title="QA-Agent")
app.add_middleware(RequestIdMiddleware)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(conversations_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/health/protected")
def protected_health(user: UserModel = Depends(get_current_user)):
    return {"email": user.email}


STATIC_DIR = os.environ.get("STATIC_DIR", "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        raise HTTPException(status_code=404)
