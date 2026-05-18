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
