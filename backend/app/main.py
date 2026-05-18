from fastapi import FastAPI, Depends
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


from app.deps import get_current_user
from app.auth.models import User as UserModel


@app.get("/api/health/protected")
def protected_health(user: UserModel = Depends(get_current_user)):
    return {"email": user.email}
