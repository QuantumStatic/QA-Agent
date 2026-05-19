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
