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
