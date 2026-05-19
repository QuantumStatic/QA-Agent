# QA-Agent — Python Port Design

**Goal:** Replicate the Spring Boot + Python AI service RAG project as a single Python service, preserving feature parity with the React frontend unchanged.

**Source project:** Financial-Advisor-Document-QA (Java backend + FastAPI AI service + Kafka).

---

## Architecture

Two Python processes share one codebase:
- **web** — FastAPI serving HTTP, dispatching Celery tasks
- **worker** — Celery worker consuming async tasks (PDF ingestion)

```
React (Vite) ──▶ FastAPI ──▶ Postgres (auth, docs, conversations)
                   │
                   ├──▶ Redis (Celery broker + result backend)
                   │
                   └──▶ ChromaDB (vector store)

              Celery worker ──▶ Postgres + ChromaDB + Groq
              (separate process, same code package)
```

No HTTP between processes. RAG is an in-process function call.

---

## Stack

| Layer | Choice |
|---|---|
| Web framework | FastAPI |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x (sync) |
| Migrations | Alembic |
| Auth | python-jose (JWT, HS256), passlib[bcrypt] |
| Async tasks | Celery + Redis |
| LLM | langchain-groq (`llama-3.3-70b-versatile`) |
| Agent | LangChain + LangGraph |
| Vector store | ChromaDB |
| Logging | structlog (JSON) with X-Request-Id middleware |
| Frontend | React + Vite + Tailwind (identical to source project) |
| Containers | Docker Compose |

---

## Project structure

```
QA-Agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint, static mount, lifespan
│   │   ├── celery_app.py        # Celery entrypoint
│   │   ├── config.py            # env-driven settings
│   │   ├── db.py                # SQLAlchemy engine, Session, Base
│   │   ├── deps.py              # FastAPI deps: db, current_user, request_id
│   │   ├── auth/
│   │   │   ├── routes.py        # POST /api/auth/register, /login
│   │   │   ├── service.py
│   │   │   ├── jwt_utils.py
│   │   │   ├── schemas.py       # Pydantic request/response
│   │   │   └── models.py        # User SQLAlchemy model
│   │   ├── documents/
│   │   │   ├── routes.py        # POST/GET/DELETE /api/documents
│   │   │   ├── service.py
│   │   │   ├── tasks.py         # @celery.task ingest_document
│   │   │   ├── schemas.py
│   │   │   └── models.py        # Document model
│   │   ├── conversations/
│   │   │   ├── routes.py        # /api/conversations + messages
│   │   │   ├── service.py
│   │   │   ├── schemas.py
│   │   │   └── models.py        # Conversation, Message
│   │   ├── rag/
│   │   │   ├── agent.py         # LangGraph state machine
│   │   │   ├── ingest.py        # PDF chunking, ChromaDB writes
│   │   │   └── chroma.py        # ChromaDB client + collection helper
│   │   ├── middleware/
│   │   │   └── request_id.py
│   │   └── logging_config.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/            # migration files
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                    # ported from source project, unchanged
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## REST API (verbatim with source project, so React frontend works unchanged)

| Method | Path | Auth | Body / Query | Response |
|---|---|---|---|---|
| POST | `/api/auth/register` | no | `{email, password}` | `{token}` |
| POST | `/api/auth/login` | no | `{email, password}` | `{token}` |
| POST | `/api/documents` | yes | multipart `file` (PDF, ≤25MB) | `{id, filename, status: "PROCESSING", uploadedAt}` |
| GET | `/api/documents?page=&size=` | yes | — | `{content: [...], totalElements, ...}` |
| DELETE | `/api/documents/{id}` | yes | — | 204 |
| GET | `/api/conversations?page=&size=` | yes | — | `{content: [...]}` |
| POST | `/api/conversations` | yes | `{title?, documentIds?}` | `{id, title, documentIds, ...}` |
| GET | `/api/conversations/{id}` | yes | — | `{id, title, documentIds, ...}` |
| DELETE | `/api/conversations/{id}` | yes | — | 204 |
| GET | `/api/conversations/{id}/messages?before=&size=` | yes | cursor pagination | `{content: [...], hasMore}` |
| POST | `/api/conversations/{id}/messages` | yes | `{message, documentIds}` | assistant message with sources |

Headers used on every request: `Authorization: Bearer <jwt>`, `X-Request-Id` (generated client-side, propagated through logs).

---

## Data model (mirrors source project)

**users** (id UUID PK, email UNIQUE, password_hash, created_at)

**documents** (id UUID PK, user_id FK, filename, file_size, status CHECK IN ("PROCESSING","READY","FAILED"), uploaded_at)

**conversations** (id UUID PK, user_id FK, title, document_ids JSONB[], created_at, updated_at)

**messages** (id UUID PK, conversation_id FK, role CHECK IN ("USER","ASSISTANT"), content TEXT, sources JSONB, created_at) with composite index `(conversation_id, created_at DESC)`.

---

## Flows

### Document upload (async)

```
1. Client POST /api/documents (PDF, JWT)
2. FastAPI: validate content-type, size ≤ 25MB, get current_user
3. Save file to /data/uploads/{doc_id}.pdf (shared volume)
4. INSERT documents row, status=PROCESSING
5. celery.send_task("documents.ingest", args=[doc_id, user_id, filename, file_path, request_id])
6. Return 201 {id, status: "PROCESSING"} immediately

[Async — Celery worker]
7. Worker reads PDF, splits, embeds, writes chunks to ChromaDB (metadata: document_id, user_id, filename, page)
8. UPDATE documents SET status="READY"  (or FAILED + error logged)
9. Delete file from /data/uploads
10. On failure: 3 retries with exponential backoff, then status=FAILED
```

### Chat

```
1. Client POST /api/conversations/{id}/messages {message, documentIds}
2. FastAPI: verify ownership, INSERT user message
3. Fetch last 20 messages (history)
4. Call rag.agent.run_agent(message, user_id, documentIds, history)
   → LangGraph: retrieve → assess → refine (loop ≤10) → generate
5. INSERT assistant message with sources
6. Return assistant message
```

### Auth

- Register: bcrypt(password) → insert user → return JWT (HS256, 24h, payload `{sub: user_id, email, exp}`)
- Login: lookup by email → verify bcrypt → return JWT
- Protected routes: `Depends(get_current_user)` decodes JWT and returns User SQLAlchemy object

---

## Error handling

- Global FastAPI exception handlers for `HTTPException`, `IntegrityError`, `ValueError`, generic `Exception`
- Error response shape: `{error: string, requestId: string}`
- Celery: `autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=3`
- All errors logged at `error` level with `request_id`, `user_id`, `document_id` bound to structlog context

---

## Logging

- structlog configured to emit JSON
- Middleware generates/reads `X-Request-Id`, binds it to context for the request
- Celery task sets up the same binding from the task's `request_id` argument
- Every request log line includes: `method`, `path`, `status`, `duration_ms`, `request_id`, `user_id?`

---

## Testing

- `pytest` + `pytest-asyncio` for FastAPI route tests (using `TestClient`)
- SQLite in-memory for unit tests (`StaticPool`)
- Celery in `task_always_eager=True` mode for tests (no broker needed)
- ChromaDB and Groq mocked at the import-boundary
- Coverage targets: auth, document CRUD, conversation CRUD, message send (mocked LLM), RAG state machine transitions
- ~25 tests total

---

## Docker Compose

```
services:
  web:        FastAPI on uvicorn, port 8080, serves React static files
  worker:     Celery worker, same image, command: celery -A app.celery_app worker
  postgres:   PostgreSQL 15
  redis:      Redis 7  (Celery broker + result backend)
  chroma:     ChromaDB

volumes:
  postgres_data
  uploads_data    (mounted in web + worker at /data/uploads)
```

Single Dockerfile, multi-stage:
- Stage 1: `node:20-alpine` builds `frontend/dist`
- Stage 2: `python:3.11-slim` installs deps, copies app + frontend dist to `app/static/`

`web` and `worker` use the same image with different commands.

---

## Out of scope

- WebSockets / SSE for live document status updates (client polls instead)
- Embedding model swap (ChromaDB default `all-MiniLM-L6-v2` is fine)
- Multi-tenancy beyond per-user filtering
- File storage in S3 / object store (shared Docker volume is sufficient)
