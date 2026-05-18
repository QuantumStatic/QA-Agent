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
    request_id = getattr(request.state, "request_id", "test-req-id")
    doc = service.upload_document(db, file, str(user.id), request_id)
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
