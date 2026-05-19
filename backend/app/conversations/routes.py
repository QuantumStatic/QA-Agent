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
