from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://qa_user:qa_pass@localhost:5432/qa_agent"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-please-min-32-characters-long-xx"  # DEV ONLY — override via JWT_SECRET env var
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

    model_config = {"env_file": ".env"}


settings = Settings()
