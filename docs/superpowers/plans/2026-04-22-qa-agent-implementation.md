# QA-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-Python-service RAG document Q&A app with feature parity to the source Spring Boot + FastAPI project, using FastAPI + Celery + SQLAlchemy + LangGraph.

**Architecture:** Single FastAPI process (web tier) dispatches Celery tasks via Redis broker. Celery worker process consumes ingestion tasks. Both processes share one Python package (`app/`). Same React frontend, ChromaDB for vectors, Postgres for metadata.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.x (sync), Alembic, Celery, Redis, python-jose, passlib[bcrypt], structlog, LangChain, LangGraph, langchain-groq, ChromaDB, pytest, React + Vite + Tailwind.

**Repo:** `/Users/utkarsh/Desktop/Utkarsh/personal/repos/QA-Agent`
**Branch:** create `feature/implementation` from `main` before starting

**Source code to reference** (for porting, not to copy verbatim — adapt to single-service):
`/Users/utkarsh/Desktop/Utkarsh/personal/repos/Financial-Advisor-Document-QA/` on `main`. Reusable parts include:
- `ai-service/app/agent.py` — LangGraph state machine (port nearly as-is)
- `ai-service/app/ingest.py` — chunking logic
- `frontend/` — copy verbatim, only `vite.config.js` proxy stays pointed at `http://localhost:8080`

**Important conventions:**
- All commits use plain `git commit -m "..."` — never `Co-Authored-By`
- Never `git push` from this session — user pushes manually
- Tests use `pytest`. SQLite in-memory for tests. Celery in `task_always_eager=True` for tests.

---

## File Structure

```
QA-Agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── celery_app.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── deps.py
│   │   ├── logging_config.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── request_id.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── jwt_utils.py
│   │   │   ├── service.py
│   │   │   └── routes.py
│   │   ├── documents/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── tasks.py
│   │   │   └── routes.py
│   │   ├── conversations/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── routes.py
│   │   └── rag/
│   │       ├── __init__.py
│   │       ├── chroma.py
│   │       ├── ingest.py
│   │       └── agent.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── alembic.ini
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_documents.py
│   │   ├── test_conversations.py
│   │   └── test_rag.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                          (copied verbatim from source project)
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py` (empty)
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create branch**

```bash
cd /Users/utkarsh/Desktop/Utkarsh/personal/repos/QA-Agent
git checkout -b feature/implementation
```

- [ ] **Step 2: Create `backend/pyproject.toml`**

```toml
[project]
name = "qa-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi==0.111.0",
    "uvicorn[standard]==0.29.0",
    "pydantic==2.7.1",
    "pydantic-settings==2.2.1",
    "sqlalchemy==2.0.30",
    "alembic==1.13.1",
    "psycopg2-binary==2.9.9",
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "python-multipart==0.0.9",
    "celery[redis]==5.4.0",
    "redis==5.0.4",
    "structlog==24.1.0",
    "langchain==0.2.16",
    "langchain-groq==0.1.10",
    "langchain-chroma==0.1.4",
    "langchain-community==0.2.16",
    "langchain-text-splitters==0.2.4",
    "langgraph==0.2.34",
    "chromadb==0.5.5",
    "pypdf==4.2.0",
    "httpx==0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest==8.2.0",
    "pytest-asyncio==0.23.6",
    "pytest-mock==3.14.0",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 3: Create `backend/app/config.py`**

```python
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://qa_user:qa_pass@localhost:5432/qa_agent"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-please-min-32-characters-long-xx"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    groq_api_key: str = "placeholder"
    groq_model: str = "llama-3.3-70b-versatile"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "qa_docs"
    uploads_dir: str = "/data/uploads"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_iterations: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: Create `.env.example`**

```
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET=replace_with_a_secure_random_string_at_least_32_chars
DB_NAME=qa_agent
DB_USER=qa_user
DB_PASSWORD=qa_pass
```

- [ ] **Step 5: Create `.gitignore`**

```
__pycache__/
**/__pycache__/
*.pyc
*.pyo
.venv/
backend/.venv/
node_modules/
frontend/node_modules/
frontend/dist/
.env
.idea/
.vscode/
.claude/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 6: Create `backend/app/__init__.py` and `backend/tests/__init__.py`** (both empty)

- [ ] **Step 7: Verify Python imports work**

```bash
cd /Users/utkarsh/Desktop/Utkarsh/personal/repos/QA-Agent/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -c "from app.config import settings; print(settings.database_url)"
```

Expected: prints `postgresql+psycopg2://qa_user:qa_pass@localhost:5432/qa_agent`

- [ ] **Step 8: Commit**

```bash
cd /Users/utkarsh/Desktop/Utkarsh/personal/repos/QA-Agent
git add backend/pyproject.toml backend/app/__init__.py backend/app/config.py backend/tests/__init__.py .env.example .gitignore
git commit -m "feat: scaffold backend package and config"
```

---

## Task 2: DB Layer + SQLAlchemy Models

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/auth/__init__.py` (empty)
- Create: `backend/app/auth/models.py`
- Create: `backend/app/documents/__init__.py` (empty)
- Create: `backend/app/documents/models.py`
- Create: `backend/app/conversations/__init__.py` (empty)
- Create: `backend/app/conversations/models.py`

- [ ] **Step 1: Create `backend/app/db.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Create `backend/app/auth/models.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

- [ ] **Step 3: Create `backend/app/documents/models.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("status IN ('PROCESSING','READY','FAILED')", name="documents_status_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PROCESSING")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

- [ ] **Step 4: Create `backend/app/conversations/models.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Conversation")
    document_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('USER','ASSISTANT')", name="messages_role_check"),
        Index("idx_messages_conv_created", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

- [ ] **Step 5: Verify models import without errors**

```bash
cd backend && python -c "from app.auth.models import User; from app.documents.models import Document; from app.conversations.models import Conversation, Message; print('models ok')"
```

Expected: prints `models ok`

- [ ] **Step 6: Commit**

```bash
git add backend/app/db.py backend/app/auth/__init__.py backend/app/auth/models.py backend/app/documents/__init__.py backend/app/documents/models.py backend/app/conversations/__init__.py backend/app/conversations/models.py
git commit -m "feat: SQLAlchemy 2.x models for users, documents, conversations, messages"
```

---

## Task 3: Alembic Setup + Initial Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_initial.py`

- [ ] **Step 1: Initialize Alembic**

```bash
cd backend && alembic init alembic
```

This generates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, and `alembic/versions/`.

- [ ] **Step 2: Edit `backend/alembic.ini`** — set `sqlalchemy.url` to empty (will be set from env):

Replace the `sqlalchemy.url` line with:
```ini
sqlalchemy.url =
```

- [ ] **Step 3: Replace `backend/alembic/env.py`** with this content:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.config import settings
from app.db import Base
from app.auth.models import User  # noqa: F401
from app.documents.models import Document  # noqa: F401
from app.conversations.models import Conversation, Message  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Create initial migration file**

```bash
cd backend && alembic revision --autogenerate -m "initial schema" -- --rev-id 0001
```

(If alembic doesn't support `--rev-id` flag, rename the generated file to `0001_initial.py` and edit `revision = "0001"` inside.)

Verify the generated migration creates `users`, `documents`, `conversations`, `messages` tables with the expected columns.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/alembic/env.py backend/alembic/script.py.mako backend/alembic/versions/
git commit -m "feat: alembic migrations for initial schema"
```

---

## Task 4: Logging + Request ID Middleware

**Files:**
- Create: `backend/app/logging_config.py`
- Create: `backend/app/middleware/__init__.py` (empty)
- Create: `backend/app/middleware/request_id.py`

- [ ] **Step 1: Create `backend/app/logging_config.py`**

```python
import logging
import sys
import structlog


def configure_logging():
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
```

- [ ] **Step 2: Create `backend/app/middleware/request_id.py`**

```python
import uuid
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


logger = structlog.get_logger()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["x-request-id"] = request_id
        return response
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/logging_config.py backend/app/middleware/__init__.py backend/app/middleware/request_id.py
git commit -m "feat: structlog JSON logging and request-id middleware"
```

---

## Task 5: Test Infrastructure (conftest)

**Files:**
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.auth.models import User  # noqa: F401
from app.documents.models import Document  # noqa: F401
from app.conversations.models import Conversation, Message  # noqa: F401


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # SQLite doesn't support JSONB/UUID natively — patch types for test
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    from app.main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**Note:** SQLite doesn't support PostgreSQL `JSONB` and `UUID` types. The models use `from sqlalchemy.dialects.postgresql import UUID, JSONB` which fails on SQLite. Fix this by adding a TypeDecorator approach inline — see Step 2.

- [ ] **Step 2: Update `backend/app/db.py`** to handle SQLite-compatible types

Replace the file with:

```python
import uuid
import json
from sqlalchemy import create_engine, String, TypeDecorator, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.types import TypeEngine
from app.config import settings


class GUID(TypeDecorator):
    """UUID type that uses Postgres UUID if available, else stores as string."""
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class JSONType(TypeDecorator):
    """JSON type that uses Postgres JSONB if available, else stores as TEXT JSON."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.loads(value)


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Update models to use `GUID` and `JSONType`**

In `backend/app/auth/models.py`, replace `from sqlalchemy.dialects.postgresql import UUID` with `from app.db import GUID` and `UUID(as_uuid=True)` with `GUID`.

In `backend/app/documents/models.py`, replace `from sqlalchemy.dialects.postgresql import UUID` with `from app.db import GUID` and `UUID(as_uuid=True)` with `GUID`.

In `backend/app/conversations/models.py`, replace `from sqlalchemy.dialects.postgresql import UUID, JSONB` with `from app.db import GUID, JSONType` and use `GUID` and `JSONType`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/db.py backend/app/auth/models.py backend/app/documents/models.py backend/app/conversations/models.py backend/tests/conftest.py
git commit -m "feat: SQLite-compatible UUID/JSON types and pytest conftest"
```

---

## Task 6: Auth — JWT utils, password hashing, schemas

**Files:**
- Create: `backend/app/auth/jwt_utils.py`
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests first in `backend/tests/test_auth.py`**

```python
import pytest
from app.auth.service import hash_password, verify_password, create_user, authenticate
from app.auth.jwt_utils import create_token, decode_token


def test_password_hash_roundtrip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token = create_token("user-id-123", "test@example.com")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"
    assert payload["email"] == "test@example.com"


def test_create_user_and_authenticate(db_session):
    user = create_user(db_session, "u@example.com", "pw12345")
    assert user.email == "u@example.com"
    assert user.id is not None

    authed = authenticate(db_session, "u@example.com", "pw12345")
    assert authed is not None
    assert authed.id == user.id

    assert authenticate(db_session, "u@example.com", "wrong") is None
    assert authenticate(db_session, "missing@example.com", "pw12345") is None


def test_register_and_login_endpoints(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "secretpass"})
    assert r.status_code == 200
    assert "token" in r.json()

    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "secretpass"})
    assert r.status_code == 200
    assert "token" in r.json()

    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && pytest tests/test_auth.py -v
```

Expected: ImportError on `app.auth.service` and `app.auth.jwt_utils`.

- [ ] **Step 3: Create `backend/app/auth/jwt_utils.py`**

```python
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.config import settings


def create_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
```

- [ ] **Step 4: Create `backend/app/auth/schemas.py`**

```python
from pydantic import BaseModel, EmailStr


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
```

- [ ] **Step 5: Create `backend/app/auth/service.py`**

```python
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.auth.models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_user(db: Session, email: str, password: str) -> User:
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None
```

- [ ] **Step 6: Create `backend/app/auth/routes.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth.schemas import AuthRequest, AuthResponse
from app.auth.service import create_user, authenticate
from app.auth.jwt_utils import create_token


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(req: AuthRequest, db: Session = Depends(get_db)):
    try:
        user = create_user(db, req.email, req.password)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    return AuthResponse(token=create_token(str(user.id), user.email))


@router.post("/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = authenticate(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return AuthResponse(token=create_token(str(user.id), user.email))
```

- [ ] **Step 7: Create minimal `backend/app/main.py` so tests can run**

```python
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
```

- [ ] **Step 8: Run tests, verify all pass**

```bash
cd backend && pytest tests/test_auth.py -v
```

Expected: 4 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/app/auth/jwt_utils.py backend/app/auth/schemas.py backend/app/auth/service.py backend/app/auth/routes.py backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: JWT auth with register and login endpoints"
```

---

## Task 7: Current User Dependency

**Files:**
- Create: `backend/app/deps.py`

- [ ] **Step 1: Add test in `backend/tests/test_auth.py` (append to existing file)**

```python
def test_current_user_dependency(client):
    r = client.post("/api/auth/register", json={"email": "x@y.com", "password": "pwpwpwpw"})
    token = r.json()["token"]

    r = client.get("/api/health/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "x@y.com"

    r = client.get("/api/health/protected")
    assert r.status_code == 401

    r = client.get("/api/health/protected", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run test, verify failure**

```bash
cd backend && pytest tests/test_auth.py::test_current_user_dependency -v
```

Expected: FAIL (no `/api/health/protected` route).

- [ ] **Step 3: Create `backend/app/deps.py`**

```python
import uuid
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.models import User
from app.auth.jwt_utils import decode_token


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

- [ ] **Step 4: Add protected health endpoint in `backend/app/main.py`** — append at the bottom:

```python
from app.deps import get_current_user
from app.auth.models import User as UserModel


@app.get("/api/health/protected")
def protected_health(user: UserModel = Depends(get_current_user)):
    return {"email": user.email}
```

- [ ] **Step 5: Run test, verify pass**

```bash
cd backend && pytest tests/test_auth.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/deps.py backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: get_current_user dependency for JWT-protected routes"
```

---

## Task 8: ChromaDB Client + Ingest Logic

**Files:**
- Create: `backend/app/rag/__init__.py` (empty)
- Create: `backend/app/rag/chroma.py`
- Create: `backend/app/rag/ingest.py`

- [ ] **Step 1: Create `backend/app/rag/__init__.py`** (empty)

- [ ] **Step 2: Create `backend/app/rag/chroma.py`**

```python
import chromadb
from app.config import settings


def get_chroma_collection():
    client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return client.get_or_create_collection(settings.chroma_collection)
```

- [ ] **Step 3: Create `backend/app/rag/ingest.py`**

```python
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.rag.chroma import get_chroma_collection


def ingest_pdf(file_path: str, document_id: str, user_id: str, filename: str) -> int:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    loader = PyPDFLoader(file_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(docs)

    collection = get_chroma_collection()
    ids = [f"{document_id}-{i}" for i in range(len(chunks))]
    texts = [c.page_content for c in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "page": c.metadata.get("page", 0),
        }
        for c in chunks
    ]
    collection.add(ids=ids, documents=texts, metadatas=metadatas)
    return len(chunks)


def delete_document_from_chroma(document_id: str):
    collection = get_chroma_collection()
    results = collection.get(where={"document_id": {"$eq": document_id}})
    if results["ids"]:
        collection.delete(ids=results["ids"])
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/rag/__init__.py backend/app/rag/chroma.py backend/app/rag/ingest.py
git commit -m "feat: ChromaDB client and PDF ingestion logic"
```

---

## Task 9: LangGraph RAG Agent

**Files:**
- Create: `backend/app/rag/agent.py`

- [ ] **Step 1: Create `backend/app/rag/agent.py`**

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq

from app.config import settings
from app.rag.chroma import get_chroma_collection


class AgentState(TypedDict):
    message: str
    user_id: str
    document_ids: list[str]
    conversation_history: list[dict]
    retrieved_chunks: list[dict]
    query: str
    iterations: int
    answer: str
    sufficient: bool


def _llm():
    return ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0)


def retrieve_chunks(state: AgentState) -> AgentState:
    collection = get_chroma_collection()
    query = state.get("query") or state["message"]
    doc_ids = state["document_ids"]
    if not doc_ids:
        return {**state, "retrieved_chunks": [], "iterations": state["iterations"] + 1}

    if len(doc_ids) == 1:
        where_filter = {"$and": [
            {"document_id": {"$eq": doc_ids[0]}},
            {"user_id": {"$eq": state["user_id"]}},
        ]}
    else:
        where_filter = {"$and": [
            {"document_id": {"$in": doc_ids}},
            {"user_id": {"$eq": state["user_id"]}},
        ]}

    results = collection.query(query_texts=[query], n_results=5, where=where_filter)
    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({
            "text": doc,
            "filename": meta.get("filename"),
            "page": meta.get("page"),
            "document_id": meta.get("document_id"),
        })
    return {**state, "retrieved_chunks": chunks, "iterations": state["iterations"] + 1}


def assess_sufficiency(state: AgentState) -> AgentState:
    if state["iterations"] >= settings.max_iterations or not state["document_ids"]:
        return {**state, "sufficient": True}
    context = "\n".join(c["text"] for c in state["retrieved_chunks"])
    prompt = (
        f"Given this context:\n{context}\n\n"
        f'Can you fully answer: "{state["message"]}"?\n'
        f"Reply with only YES or NO."
    )
    response = _llm().invoke(prompt)
    sufficient = "YES" in response.content.upper()
    return {**state, "sufficient": sufficient}


def refine_query(state: AgentState) -> AgentState:
    prompt = (
        f'Original question: {state["message"]}\n'
        f'Current search query: {state.get("query", state["message"])}\n'
        f"The retrieved context was insufficient. Generate a different, more specific search query.\n"
        f"Reply with only the new query."
    )
    response = _llm().invoke(prompt)
    return {**state, "query": response.content.strip()}


def generate_answer(state: AgentState) -> AgentState:
    context = "\n\n".join(
        f"[{c['filename']} p.{c['page']}]: {c['text']}"
        for c in state["retrieved_chunks"]
    )
    history = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}"
        for m in state["conversation_history"][-6:]
    )
    prompt = (
        f"You are a helpful assistant that answers questions based on the provided documents.\n\n"
        f"Conversation history:\n{history}\n\n"
        f"Retrieved context:\n{context}\n\n"
        f"Answer the question: {state['message']}\n"
        f"Be concise and cite the document filename when relevant."
    )
    response = _llm().invoke(prompt)
    return {**state, "answer": response.content}


def should_continue(state: AgentState) -> str:
    if state["sufficient"] or state["iterations"] >= settings.max_iterations:
        return "generate"
    return "refine"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_chunks)
    graph.add_node("assess", assess_sufficiency)
    graph.add_node("refine", refine_query)
    graph.add_node("generate", generate_answer)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "assess")
    graph.add_conditional_edges("assess", should_continue, {
        "generate": "generate",
        "refine": "refine",
    })
    graph.add_edge("refine", "retrieve")
    graph.add_edge("generate", END)
    return graph.compile()


_graph = build_graph()


def run_agent(message: str, user_id: str, document_ids: list[str], history: list[dict]) -> dict:
    state: AgentState = {
        "message": message,
        "user_id": user_id,
        "document_ids": document_ids,
        "conversation_history": history,
        "retrieved_chunks": [],
        "query": message,
        "iterations": 0,
        "answer": "",
        "sufficient": False,
    }
    result = _graph.invoke(state)
    sources = [{
        "documentId": c["document_id"],
        "filename": c["filename"],
        "page": c["page"],
        "excerpt": c["text"][:200],
    } for c in result["retrieved_chunks"][:3]]
    return {
        "answer": result["answer"],
        "sources": sources,
        "iterations_used": result["iterations"],
    }
```

- [ ] **Step 2: Create `backend/tests/test_rag.py`**

```python
from unittest.mock import patch, MagicMock
from app.rag.agent import run_agent


def test_run_agent_no_documents():
    """When document_ids is empty, agent skips assessment loop and just generates."""
    with patch("app.rag.agent._llm") as mock_llm:
        mock_response = MagicMock()
        mock_response.content = "I don't have any documents to answer from."
        mock_llm.return_value.invoke.return_value = mock_response

        result = run_agent(
            message="hello",
            user_id="u1",
            document_ids=[],
            history=[],
        )
        assert "answer" in result
        assert result["sources"] == []
        assert result["iterations_used"] >= 1


def test_run_agent_with_documents():
    """With documents, agent retrieves chunks and generates answer."""
    fake_chunks = {
        "documents": [["Some text from PDF"]],
        "metadatas": [[{"filename": "test.pdf", "page": 1, "document_id": "doc1", "user_id": "u1"}]],
    }
    with patch("app.rag.agent.get_chroma_collection") as mock_chroma, \
         patch("app.rag.agent._llm") as mock_llm:
        mock_chroma.return_value.query.return_value = fake_chunks
        # First LLM call (assess) returns YES → go straight to generate
        # Second LLM call (generate) returns the answer
        sufficient = MagicMock(); sufficient.content = "YES"
        answer = MagicMock(); answer.content = "Based on test.pdf, the answer is 42."
        mock_llm.return_value.invoke.side_effect = [sufficient, answer]

        result = run_agent(
            message="what is the answer?",
            user_id="u1",
            document_ids=["doc1"],
            history=[],
        )
        assert "42" in result["answer"]
        assert len(result["sources"]) == 1
        assert result["sources"][0]["filename"] == "test.pdf"
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_rag.py -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/rag/agent.py backend/tests/test_rag.py
git commit -m "feat: LangGraph agentic RAG with up to 10 refinement iterations"
```

---

## Task 10: Celery App + Document Ingest Task

**Files:**
- Create: `backend/app/celery_app.py`
- Create: `backend/app/documents/tasks.py`

- [ ] **Step 1: Create `backend/app/celery_app.py`**

```python
from celery import Celery
from app.config import settings


celery_app = Celery(
    "qa_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.documents.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

- [ ] **Step 2: Create `backend/app/documents/tasks.py`**

```python
import os
import uuid
import structlog
from app.celery_app import celery_app
from app.db import SessionLocal
from app.documents.models import Document
from app.rag.ingest import ingest_pdf


logger = structlog.get_logger()


@celery_app.task(
    name="documents.ingest",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def ingest_document_task(self, document_id: str, user_id: str, filename: str, file_path: str, request_id: str):
    structlog.contextvars.bind_contextvars(request_id=request_id, document_id=document_id)
    logger.info("ingest_task_started")
    db = SessionLocal()
    try:
        chunk_count = ingest_pdf(file_path, document_id, user_id, filename)
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if doc:
            doc.status = "READY"
            db.commit()
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.info("ingest_task_complete", chunk_count=chunk_count)
        return {"document_id": document_id, "chunk_count": chunk_count, "status": "READY"}
    except Exception as e:
        logger.error("ingest_task_failed", error=str(e))
        if self.request.retries >= self.max_retries:
            doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
            if doc:
                doc.status = "FAILED"
                db.commit()
            if os.path.exists(file_path):
                os.remove(file_path)
        raise
    finally:
        db.close()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/celery_app.py backend/app/documents/tasks.py
git commit -m "feat: Celery worker and document ingest task with retries"
```

---

## Task 11: Documents — Schemas, Service, Routes

**Files:**
- Create: `backend/app/documents/schemas.py`
- Create: `backend/app/documents/service.py`
- Create: `backend/app/documents/routes.py`
- Create: `backend/tests/test_documents.py`

- [ ] **Step 1: Write failing tests in `backend/tests/test_documents.py`**

```python
import io
import pytest
from unittest.mock import patch


def _register(client, email="d@e.com", password="pwpwpwpw"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    return r.json()["token"]


def test_upload_document(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.documents.service.settings.uploads_dir", str(tmp_path))
    token = _register(client)
    pdf_bytes = b"%PDF-1.4 minimal"

    with patch("app.documents.service.ingest_document_task") as mock_task:
        mock_task.delay.return_value = None
        r = client.post(
            "/api/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "test.pdf"
    assert body["status"] == "PROCESSING"
    assert "id" in body


def test_upload_rejects_non_pdf(client):
    token = _register(client)
    r = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 400


def test_list_documents(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.documents.service.settings.uploads_dir", str(tmp_path))
    token = _register(client)
    pdf_bytes = b"%PDF-1.4 minimal"
    with patch("app.documents.service.ingest_document_task"):
        client.post(
            "/api/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("a.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
    r = client.get("/api/documents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["totalElements"] == 1
    assert body["content"][0]["filename"] == "a.pdf"


def test_delete_document(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.documents.service.settings.uploads_dir", str(tmp_path))
    token = _register(client)
    pdf_bytes = b"%PDF-1.4 minimal"
    with patch("app.documents.service.ingest_document_task"):
        r = client.post(
            "/api/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("b.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
    doc_id = r.json()["id"]
    with patch("app.documents.service.delete_document_from_chroma"):
        r = client.delete(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
```

- [ ] **Step 2: Run tests, verify failures**

```bash
cd backend && pytest tests/test_documents.py -v
```

Expected: import errors / 404s.

- [ ] **Step 3: Create `backend/app/documents/schemas.py`**

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class DocumentDTO(BaseModel):
    id: UUID
    filename: str
    fileSize: int
    status: str
    uploadedAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, doc):
        return cls(
            id=doc.id,
            filename=doc.filename,
            fileSize=doc.file_size,
            status=doc.status,
            uploadedAt=doc.uploaded_at,
        )


class DocumentPage(BaseModel):
    content: list[DocumentDTO]
    totalElements: int
    page: int
    size: int
```

- [ ] **Step 4: Create `backend/app/documents/service.py`**

```python
import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.documents.models import Document
from app.documents.tasks import ingest_document_task
from app.rag.ingest import delete_document_from_chroma


MAX_BYTES = 25 * 1024 * 1024


def upload_document(db: Session, file: UploadFile, user_id: str, request_id: str) -> Document:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = file.file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 25MB limit")

    doc = Document(
        user_id=uuid.UUID(user_id),
        filename=file.filename or "untitled.pdf",
        file_size=len(contents),
        status="PROCESSING",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    uploads_path = Path(settings.uploads_dir)
    uploads_path.mkdir(parents=True, exist_ok=True)
    file_path = uploads_path / f"{doc.id}.pdf"
    file_path.write_bytes(contents)

    ingest_document_task.delay(
        str(doc.id), user_id, doc.filename, str(file_path), request_id
    )
    return doc


def list_documents(db: Session, user_id: str, page: int, size: int) -> tuple[list[Document], int]:
    q = db.query(Document).filter(Document.user_id == uuid.UUID(user_id))
    total = q.count()
    items = q.order_by(Document.uploaded_at.desc()).offset(page * size).limit(size).all()
    return items, total


def delete_document(db: Session, document_id: str, user_id: str):
    doc = db.query(Document).filter(
        Document.id == uuid.UUID(document_id),
        Document.user_id == uuid.UUID(user_id),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document_from_chroma(document_id)
    db.delete(doc)
    db.commit()
```

- [ ] **Step 5: Create `backend/app/documents/routes.py`**

```python
from fastapi import APIRouter, Depends, UploadFile, File, Request, Response, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.auth.models import User
from app.documents.schemas import DocumentDTO, DocumentPage
from app.documents import service


router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", status_code=201, response_model=DocumentDTO)
def upload(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = service.upload_document(db, file, str(user.id), request.state.request_id)
    return DocumentDTO.from_model(doc)


@router.get("", response_model=DocumentPage)
def list_docs(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = service.list_documents(db, str(user.id), page, size)
    return DocumentPage(
        content=[DocumentDTO.from_model(d) for d in items],
        totalElements=total,
        page=page,
        size=size,
    )


@router.delete("/{document_id}", status_code=204)
def delete(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service.delete_document(db, document_id, str(user.id))
    return Response(status_code=204)
```

- [ ] **Step 6: Wire route into `backend/app/main.py`** — add this line near the auth router include:

```python
from app.documents.routes import router as documents_router
app.include_router(documents_router)
```

- [ ] **Step 7: Run tests, verify all pass**

```bash
cd backend && pytest tests/test_documents.py -v
```

Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/documents/schemas.py backend/app/documents/service.py backend/app/documents/routes.py backend/app/main.py backend/tests/test_documents.py
git commit -m "feat: document upload, list, delete with Celery async ingestion"
```

---

## Task 12: Conversations — Schemas, Service, Routes

**Files:**
- Create: `backend/app/conversations/schemas.py`
- Create: `backend/app/conversations/service.py`
- Create: `backend/app/conversations/routes.py`
- Create: `backend/tests/test_conversations.py`

- [ ] **Step 1: Write failing tests in `backend/tests/test_conversations.py`**

```python
from unittest.mock import patch


def _register(client, email="c@d.com", password="pwpwpwpw"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    return r.json()["token"]


def test_create_conversation(client):
    token = _register(client)
    r = client.post(
        "/api/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "test", "documentIds": []},
    )
    assert r.status_code == 201
    assert r.json()["title"] == "test"


def test_list_conversations(client):
    token = _register(client)
    client.post("/api/conversations", headers={"Authorization": f"Bearer {token}"}, json={})
    r = client.get("/api/conversations", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["totalElements"] == 1


def test_delete_conversation(client):
    token = _register(client)
    r = client.post("/api/conversations", headers={"Authorization": f"Bearer {token}"}, json={})
    cid = r.json()["id"]
    r = client.delete(f"/api/conversations/{cid}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204


def test_send_message_and_get_response(client):
    token = _register(client)
    r = client.post("/api/conversations", headers={"Authorization": f"Bearer {token}"}, json={})
    cid = r.json()["id"]

    with patch("app.conversations.service.run_agent") as mock_agent:
        mock_agent.return_value = {
            "answer": "mock answer",
            "sources": [],
            "iterations_used": 1,
        }
        r = client.post(
            f"/api/conversations/{cid}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "hello", "documentIds": []},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "ASSISTANT"
    assert body["content"] == "mock answer"


def test_list_messages_cursor_pagination(client):
    token = _register(client)
    r = client.post("/api/conversations", headers={"Authorization": f"Bearer {token}"}, json={})
    cid = r.json()["id"]

    with patch("app.conversations.service.run_agent") as mock_agent:
        mock_agent.return_value = {"answer": "a", "sources": [], "iterations_used": 1}
        for i in range(3):
            client.post(
                f"/api/conversations/{cid}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": f"q{i}", "documentIds": []},
            )

    r = client.get(f"/api/conversations/{cid}/messages?size=10", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["content"]) == 6  # 3 user + 3 assistant
    assert body["hasMore"] is False
```

- [ ] **Step 2: Run tests, verify failures**

```bash
cd backend && pytest tests/test_conversations.py -v
```

Expected: import errors / 404s.

- [ ] **Step 3: Create `backend/app/conversations/schemas.py`**

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = None
    documentIds: list[UUID] = Field(default_factory=list)


class ConversationDTO(BaseModel):
    id: UUID
    title: str
    documentIds: list[UUID]
    createdAt: datetime
    updatedAt: datetime

    @classmethod
    def from_model(cls, c):
        return cls(
            id=c.id,
            title=c.title,
            documentIds=c.document_ids or [],
            createdAt=c.created_at,
            updatedAt=c.updated_at,
        )


class ConversationPage(BaseModel):
    content: list[ConversationDTO]
    totalElements: int
    page: int
    size: int


class SendMessageRequest(BaseModel):
    message: str
    documentIds: list[UUID] = Field(default_factory=list)


class SourceDTO(BaseModel):
    documentId: str | None = None
    filename: str | None = None
    page: int | None = None
    excerpt: str | None = None


class MessageDTO(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list[SourceDTO] = Field(default_factory=list)
    createdAt: datetime

    @classmethod
    def from_model(cls, m):
        return cls(
            id=m.id,
            role=m.role,
            content=m.content,
            sources=[SourceDTO(**s) if isinstance(s, dict) else s for s in (m.sources or [])],
            createdAt=m.created_at,
        )


class MessagePage(BaseModel):
    content: list[MessageDTO]
    hasMore: bool
```

- [ ] **Step 4: Create `backend/app/conversations/service.py`**

```python
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.conversations.models import Conversation, Message
from app.conversations.schemas import ConversationCreate, SendMessageRequest
from app.rag.agent import run_agent


def create_conversation(db: Session, req: ConversationCreate, user_id: str) -> Conversation:
    conv = Conversation(
        user_id=uuid.UUID(user_id),
        title=req.title or "New Conversation",
        document_ids=[str(d) for d in (req.documentIds or [])],
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def list_conversations(db: Session, user_id: str, page: int, size: int) -> tuple[list[Conversation], int]:
    q = db.query(Conversation).filter(Conversation.user_id == uuid.UUID(user_id))
    total = q.count()
    items = q.order_by(Conversation.updated_at.desc()).offset(page * size).limit(size).all()
    return items, total


def get_conversation(db: Session, conversation_id: str, user_id: str) -> Conversation:
    conv = db.query(Conversation).filter(
        Conversation.id == uuid.UUID(conversation_id),
        Conversation.user_id == uuid.UUID(user_id),
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def delete_conversation(db: Session, conversation_id: str, user_id: str):
    conv = get_conversation(db, conversation_id, user_id)
    db.delete(conv)
    db.commit()


def send_message(db: Session, conversation_id: str, user_id: str, req: SendMessageRequest) -> Message:
    conv = get_conversation(db, conversation_id, user_id)

    user_msg = Message(
        conversation_id=conv.id, role="USER", content=req.message, sources=[],
    )
    db.add(user_msg)
    db.commit()

    history = db.query(Message).filter(Message.conversation_id == conv.id) \
        .order_by(Message.created_at.asc()).all()
    history_dicts = [{"role": m.role, "content": m.content} for m in history]

    result = run_agent(
        message=req.message,
        user_id=user_id,
        document_ids=[str(d) for d in (req.documentIds or [])],
        history=history_dicts,
    )

    assistant_msg = Message(
        conversation_id=conv.id,
        role="ASSISTANT",
        content=result["answer"],
        sources=result.get("sources", []),
    )
    db.add(assistant_msg)

    from datetime import datetime
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


def list_messages(db: Session, conversation_id: str, user_id: str, before: str | None, size: int) -> tuple[list[Message], bool]:
    get_conversation(db, conversation_id, user_id)
    q = db.query(Message).filter(Message.conversation_id == uuid.UUID(conversation_id))
    if before:
        before_msg = db.query(Message).filter(Message.id == uuid.UUID(before)).first()
        if before_msg:
            q = q.filter(Message.created_at < before_msg.created_at)
    items = q.order_by(Message.created_at.desc()).limit(size + 1).all()
    has_more = len(items) > size
    items = items[:size]
    return items, has_more
```

- [ ] **Step 5: Create `backend/app/conversations/routes.py`**

```python
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.auth.models import User
from app.conversations import service
from app.conversations.schemas import (
    ConversationCreate, ConversationDTO, ConversationPage,
    SendMessageRequest, MessageDTO, MessagePage,
)


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", status_code=201, response_model=ConversationDTO)
def create(req: ConversationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = service.create_conversation(db, req, str(user.id))
    return ConversationDTO.from_model(conv)


@router.get("", response_model=ConversationPage)
def list_all(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = service.list_conversations(db, str(user.id), page, size)
    return ConversationPage(
        content=[ConversationDTO.from_model(c) for c in items],
        totalElements=total,
        page=page,
        size=size,
    )


@router.get("/{conversation_id}", response_model=ConversationDTO)
def get_one(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = service.get_conversation(db, conversation_id, str(user.id))
    return ConversationDTO.from_model(conv)


@router.delete("/{conversation_id}", status_code=204)
def delete(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_conversation(db, conversation_id, str(user.id))
    return Response(status_code=204)


@router.post("/{conversation_id}/messages", response_model=MessageDTO)
def send_message(
    conversation_id: str,
    req: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = service.send_message(db, conversation_id, str(user.id), req)
    return MessageDTO.from_model(msg)


@router.get("/{conversation_id}/messages", response_model=MessagePage)
def list_msgs(
    conversation_id: str,
    before: str | None = Query(None),
    size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, has_more = service.list_messages(db, conversation_id, str(user.id), before, size)
    return MessagePage(
        content=[MessageDTO.from_model(m) for m in items],
        hasMore=has_more,
    )
```

- [ ] **Step 6: Wire router into `backend/app/main.py`** — add:

```python
from app.conversations.routes import router as conversations_router
app.include_router(conversations_router)
```

- [ ] **Step 7: Run tests, verify all pass**

```bash
cd backend && pytest tests/test_conversations.py -v
```

Expected: 5 passed.

- [ ] **Step 8: Run all tests to verify nothing regressed**

```bash
cd backend && pytest -v
```

Expected: all green.

- [ ] **Step 9: Commit**

```bash
git add backend/app/conversations/schemas.py backend/app/conversations/service.py backend/app/conversations/routes.py backend/app/main.py backend/tests/test_conversations.py
git commit -m "feat: conversations and messages with cursor pagination"
```

---

## Task 13: Frontend Port

**Files:**
- Copy: entire `frontend/` directory from source project

- [ ] **Step 1: Copy frontend verbatim**

```bash
cp -r /Users/utkarsh/Desktop/Utkarsh/personal/repos/Financial-Advisor-Document-QA/frontend /Users/utkarsh/Desktop/Utkarsh/personal/repos/QA-Agent/frontend
```

- [ ] **Step 2: Verify build works**

```bash
cd /Users/utkarsh/Desktop/Utkarsh/personal/repos/QA-Agent/frontend && npm install && npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
cd /Users/utkarsh/Desktop/Utkarsh/personal/repos/QA-Agent
git add frontend
git commit -m "feat: copy React frontend from source project"
```

---

## Task 14: SPA Serving in FastAPI

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Update `backend/app/main.py` to serve React static files**

Replace the entire file with:

```python
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
```

- [ ] **Step 2: Run all tests** — make sure existing tests still work even without `static/` present.

```bash
cd backend && pytest -v
```

Expected: all green (the SPA catch-all only mounts when `STATIC_DIR` exists).

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: serve React SPA from FastAPI when static dir is mounted"
```

---

## Task 15: Dockerfile (multi-stage: React + Python)

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Create `backend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATIC_DIR=/app/static

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml .
RUN pip install --upgrade pip setuptools && pip install -e ".[dev]"

COPY backend/app ./app
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY --from=frontend /frontend/dist /app/static

EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8080"]
```

(The build context will be the repo root, so `COPY frontend/...` and `COPY backend/...` work.)

- [ ] **Step 2: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: multi-stage Dockerfile bundling React into FastAPI image"
```

---

## Task 16: docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  web:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      chroma:
        condition: service_started
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      REDIS_URL: redis://redis:6379/0
      CHROMA_HOST: chroma
      CHROMA_PORT: 8000
      UPLOADS_DIR: /data/uploads
    volumes:
      - uploads_data:/data/uploads
    command: ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8080"]

  worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      chroma:
        condition: service_started
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      REDIS_URL: redis://redis:6379/0
      CHROMA_HOST: chroma
      CHROMA_PORT: 8000
      UPLOADS_DIR: /data/uploads
    volumes:
      - uploads_data:/data/uploads
    command: ["celery", "-A", "app.celery_app", "worker", "--loglevel=INFO", "--concurrency=2"]

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine

  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  postgres_data:
  uploads_data:
  chroma_data:
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: docker-compose with web, celery worker, postgres, redis, chroma"
```

---

## Task 17: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace `README.md`**

```markdown
# QA-Agent — Python Agentic RAG

A document Q&A app where you upload PDFs and ask questions answered by an iterative retrieval agent.

## Stack

- **Backend** — FastAPI + Pydantic v2 (auth, documents, conversations, RAG)
- **Worker** — Celery (async PDF ingestion with retries)
- **Broker** — Redis
- **Agent** — LangGraph (retrieve → assess → refine, max 10 iterations)
- **LLM** — Groq (`llama-3.3-70b-versatile`)
- **Vector store** — ChromaDB
- **Database** — PostgreSQL with Alembic migrations
- **Frontend** — React + Vite + Tailwind (served by FastAPI)

## Architecture

```
React (Vite) → FastAPI → Postgres + Redis + ChromaDB
                            │
                            └──→ Celery worker (separate process, same image)
```

## Running locally

```bash
cp .env.example .env
# fill in GROQ_API_KEY and JWT_SECRET
docker compose up --build
```

App available at http://localhost:8080.

## Development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                      # run tests
alembic upgrade head                        # run migrations against your DB
uvicorn app.main:app --reload --port 8080   # run web tier
celery -A app.celery_app worker --loglevel=INFO  # run worker

cd ../frontend && npm install && npm run dev  # proxies /api to localhost:8080
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: project README"
```

---

## Task 18: End-to-end smoke test

- [ ] **Step 1: Build the stack**

```bash
cd /Users/utkarsh/Desktop/Utkarsh/personal/repos/QA-Agent
cp .env.example .env
# user must edit .env to set GROQ_API_KEY and a long JWT_SECRET
docker compose up --build -d
```

- [ ] **Step 2: Wait for services to be healthy, then check**

```bash
docker compose ps
curl -s http://localhost:8080/api/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Register and login**

```bash
curl -s -X POST http://localhost:8080/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"u@example.com","password":"testpass1"}'
```

Expected: `{"token":"<jwt>"}`

- [ ] **Step 4: Open the UI in browser**

Visit http://localhost:8080 — should see the login page, can register/login, then see the dashboard.

- [ ] **Step 5: Upload a small PDF, verify it transitions PROCESSING → READY**

Within ~30 seconds the document should flip from PROCESSING to READY (refresh the document list). If it stays PROCESSING, check `docker compose logs worker` for errors.

- [ ] **Step 6: Create a conversation, ask a question about the PDF**

The assistant should respond with answer + sources panel showing filename and page.

- [ ] **Step 7: Tear down**

```bash
docker compose down -v
```

- [ ] **Step 8: No new commit needed for this task** — it's verification only.

---

## Self-Review

**Spec coverage:**
- Auth (register, login, JWT, current_user) — Tasks 6, 7 ✓
- Documents (upload, list, delete, async ingestion) — Tasks 10, 11 ✓
- Conversations (CRUD, messages, cursor pagination) — Task 12 ✓
- RAG (LangGraph agent with refinement) — Task 9 ✓
- ChromaDB w/ user_id + document_id filter — Task 8 ✓
- Frontend port — Task 13 ✓
- SPA serving — Task 14 ✓
- Docker build (multi-stage React + Python) — Task 15 ✓
- Docker Compose (web, worker, postgres, redis, chroma) — Task 16 ✓
- Alembic migrations — Task 3 ✓
- structlog + X-Request-Id middleware — Task 4 ✓
- Tests for auth, documents, conversations, RAG — Tasks 6, 11, 12, 9 ✓
- E2E smoke test — Task 18 ✓

**No placeholders, no TBD, no vague language.**

**Type consistency:** `DocumentDTO.from_model`, `ConversationDTO.from_model`, `MessageDTO.from_model` follow the same pattern. `run_agent` signature consistent between definition (Task 9) and call site (Task 12). `ingest_document_task.delay(...)` arg list matches the task definition.
