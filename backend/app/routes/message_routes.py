"""
One-to-one messaging — with notification on new message.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from .notification_routes import create_notification

router = APIRouter(prefix="/messages", tags=["Messaging"])


@router.post("", response_model=schemas.MessageOut, status_code=201,
             summary="Send a message to another user")
def send_message(
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if payload.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")

    receiver = db.query(models.User).filter(models.User.id == payload.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail=f"User {payload.receiver_id} not found")

    msg = models.Message(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        content=payload.content,
    )
    db.add(msg)

    # Notify receiver
    create_notification(
        db,
        user_id=payload.receiver_id,
        type="message",
        message=f"{current_user.name} sent you a message",
        actor_id=current_user.id,
        link=f"/chat.html?user={current_user.id}",
    )

    db.commit()
    db.refresh(msg)
    return msg


@router.get("/conversations", response_model=List[schemas.ConversationPartner],
            summary="List all conversation partners")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    all_msgs = (
        db.query(models.Message)
        .filter(
            or_(
                models.Message.sender_id   == current_user.id,
                models.Message.receiver_id == current_user.id,
            )
        )
        .order_by(models.Message.created_at.desc())
        .all()
    )

    seen: set = set()
    conversations: List[schemas.ConversationPartner] = []

    for msg in all_msgs:
        partner_id = (
            msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        )
        if partner_id in seen:
            continue
        seen.add(partner_id)

        partner = db.query(models.User).filter(models.User.id == partner_id).first()
        if not partner:
            continue

        unread = db.query(models.Message).filter(
            models.Message.sender_id   == partner_id,
            models.Message.receiver_id == current_user.id,
            models.Message.is_read     == False,  # noqa: E712
        ).count()

        preview = msg.content[:80] + "…" if len(msg.content) > 80 else msg.content
        conversations.append(
            schemas.ConversationPartner(
                user=schemas.UserPublic.model_validate(partner),
                last_message=preview,
                unread_count=unread,
            )
        )

    return conversations


@router.get("/{user_id}", response_model=List[schemas.MessageOut],
            summary="Get full conversation history with a user")
def get_conversation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not db.query(models.User).filter(models.User.id == user_id).first():
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    msgs = (
        db.query(models.Message)
        .filter(
            or_(
                and_(models.Message.sender_id == current_user.id,
                     models.Message.receiver_id == user_id),
                and_(models.Message.sender_id == user_id,
                     models.Message.receiver_id == current_user.id),
            )
        )
        .order_by(models.Message.created_at.asc())
        .all()
    )

    updated = False
    for m in msgs:
        if m.receiver_id == current_user.id and not m.is_read:
            m.is_read = True
            updated = True
    if updated:
        db.commit()

    return msgs
