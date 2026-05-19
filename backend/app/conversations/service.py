import uuid
from datetime import datetime
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
    items = q.order_by(Message.created_at.asc()).limit(size + 1).all()
    has_more = len(items) > size
    items = items[:size]
    return items, has_more
