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
