"""
Notification system.

Notifications are generated server-side when:
  - Someone likes your post
  - Someone comments on your post
  - Someone sends you a mentorship request
  - A mentorship request is accepted/rejected
  - Someone sends you a direct message

GET  /notifications          — paginated list, newest first
GET  /notifications/unread   — count of unread notifications
PUT  /notifications/read-all — mark all as read
PUT  /notifications/{id}/read — mark single notification as read
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship, Session
from pydantic import BaseModel

from ..database import Base, get_db
from ..auth import get_current_user
from .. import models

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ══════════════════════════════════════════════════════════════════════════════
#  Model (extends existing Base)
# ══════════════════════════════════════════════════════════════════════════════

class Notification(Base):
    __tablename__ = "notifications"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    type        = Column(
        Enum("like", "comment", "mentorship_request", "mentorship_update",
             "message", "system", name="notification_type"),
        nullable=False,
    )
    message     = Column(Text, nullable=False)
    link        = Column(String(500))          # e.g. /dashboard.html#post-42
    is_read     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    user  = relationship("User", foreign_keys=[user_id])
    actor = relationship("User", foreign_keys=[actor_id])


# ══════════════════════════════════════════════════════════════════════════════
#  Schemas
# ══════════════════════════════════════════════════════════════════════════════

class NotificationOut(BaseModel):
    id:         int
    type:       str
    message:    str
    link:       Optional[str] = None
    is_read:    bool
    created_at: datetime
    actor:      Optional[dict] = None   # {id, name, profile_picture}

    model_config = {"from_attributes": True}


class UnreadCountOut(BaseModel):
    unread_count: int


# ══════════════════════════════════════════════════════════════════════════════
#  Helper — create a notification (called from other route modules)
# ══════════════════════════════════════════════════════════════════════════════

def create_notification(
    db: Session,
    user_id: int,
    type: str,
    message: str,
    actor_id: Optional[int] = None,
    link: Optional[str] = None,
) -> None:
    """
    Insert a notification row.  Call this from any route that should
    generate a notification (likes, comments, messages, mentorship, etc.)

    Example usage in post_routes.py after a like:
        from .notification_routes import create_notification
        create_notification(db, post.user_id, "like",
                            f"{liker.name} liked your post", actor_id=liker.id)
    """
    # Don't notify users about their own actions
    if actor_id and actor_id == user_id:
        return

    notif = Notification(
        user_id=user_id,
        actor_id=actor_id,
        type=type,
        message=message,
        link=link,
    )
    db.add(notif)
    # Note: caller is responsible for db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ══════════════════════════════════════════════════════════════════════════════

def _serialize(n: Notification) -> dict:
    actor_data = None
    if n.actor:
        actor_data = {
            "id":              n.actor.id,
            "name":            n.actor.name,
            "profile_picture": n.actor.profile_picture,
        }
    return {
        "id":         n.id,
        "type":       n.type,
        "message":    n.message,
        "link":       n.link,
        "is_read":    n.is_read,
        "created_at": n.created_at,
        "actor":      actor_data,
    }


@router.get(
    "",
    response_model=List[NotificationOut],
    summary="Get my notifications",
)
def get_notifications(
    skip:  int = 0,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return paginated notifications for the current user, newest first."""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize(n) for n in notifications]


@router.get(
    "/unread",
    response_model=UnreadCountOut,
    summary="Get unread notification count",
)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return the number of unread notifications for the nav badge."""
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,   # noqa: E712
        )
        .count()
    )
    return UnreadCountOut(unread_count=count)


@router.put(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications as read",
)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark every notification belonging to the current user as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,   # noqa: E712
    ).update({"is_read": True})
    db.commit()


@router.put(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark a single notification as read",
)
def mark_one_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a specific notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
