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

    React (Vite) → FastAPI → Postgres + Redis + ChromaDB
                               │
                               └──→ Celery worker (separate process, same image)

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
