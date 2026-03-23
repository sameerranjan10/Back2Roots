"""
Reusable FastAPI dependency functions beyond the core auth dependencies.
"""

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from .. import models
from ..config import settings


# ── Pagination ─────────────────────────────────────────────────────────────────

def pagination(
    skip: int  = Query(default=0,  ge=0,   description="Number of items to skip"),
    limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1,
                       le=settings.MAX_PAGE_SIZE, description="Max items to return"),
) -> dict:
    """Dependency that validates and returns pagination parameters."""
    return {"skip": skip, "limit": limit}


# ── Ownership / resource guards ────────────────────────────────────────────────

def get_post_or_404(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Post:
    """
    Resolve *post_id* to a Post ORM object.
    Raises HTTP 404 if not found.
    Does NOT check ownership — use `require_post_owner` for that.
    """
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found",
        )
    return post


def require_post_owner(
    post: models.Post = Depends(get_post_or_404),
    current_user: models.User = Depends(get_current_user),
) -> models.Post:
    """
    Raise HTTP 403 unless the current user owns the post or is admin.
    Returns the post on success.
    """
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this post",
        )
    return post


def get_user_or_404(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
) -> models.User:
    """
    Resolve *user_id* to a User ORM object.
    Raises HTTP 404 if not found.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user


def require_alumni_role(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Raise HTTP 403 unless the current user is an alumni."""
    if current_user.role != "alumni":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only accessible to alumni",
        )
    return current_user


def require_student_role(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Raise HTTP 403 unless the current user is a student."""
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only accessible to students",
        )
    return current_user
