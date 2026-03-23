"""
Search endpoint — full-text keyword search across users and posts.

GET /search?q=keyword&type=all|users|posts&skip=0&limit=20
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/search", tags=["Search"])


class SearchResults(schemas.MessageResponse.__class__.__base__):  # plain BaseModel
    pass


from pydantic import BaseModel

class SearchResponse(BaseModel):
    users:  List[schemas.UserPublic] = []
    posts:  List[schemas.PostOut]    = []
    total_users: int = 0
    total_posts: int = 0
    query: str       = ""


# ── helpers ───────────────────────────────────────────────────────────────────

def _serialize_post(post: models.Post, viewer_id: int) -> dict:
    return {
        "id":          post.id,
        "user_id":     post.user_id,
        "content":     post.content,
        "image_url":   post.image_url,
        "created_at":  post.created_at,
        "author":      post.author,
        "comments":    post.comments,
        "likes_count": len(post.likes),
        "liked_by_me": any(like.user_id == viewer_id for like in post.likes),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  GET /search
# ══════════════════════════════════════════════════════════════════════════════
@router.get(
    "",
    response_model=SearchResponse,
    summary="Search users and posts by keyword",
)
def search(
    q: str = Query(..., min_length=1, max_length=100, description="Search keyword"),
    type: str = Query(default="all", description="Filter: all | users | posts"),
    skip:  int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Search across the platform.

    - **q**: keyword to search (min 1 char)
    - **type**: `all` (default), `users`, or `posts`
    - Results are case-insensitive partial matches.

    **User search** — matches against: name, skills, bio, college  
    **Post search** — matches against: post content
    """
    keyword = f"%{q.strip()}%"
    users_result: List[schemas.UserPublic] = []
    posts_result: List[schemas.PostOut]    = []
    total_users = 0
    total_posts = 0

    # ── User search ───────────────────────────────────────────────────────────
    if type in ("all", "users"):
        user_query = db.query(models.User).filter(
            or_(
                models.User.name.ilike(keyword),
                models.User.skills.ilike(keyword),
                models.User.bio.ilike(keyword),
                models.User.college.ilike(keyword),
            )
        )
        total_users = user_query.count()
        users_result = [
            schemas.UserPublic.model_validate(u)
            for u in user_query.offset(skip).limit(limit).all()
        ]

    # ── Post search ───────────────────────────────────────────────────────────
    if type in ("all", "posts"):
        from sqlalchemy.orm import joinedload
        post_query = (
            db.query(models.Post)
            .options(
                joinedload(models.Post.author),
                joinedload(models.Post.comments).joinedload(models.Comment.author),
                joinedload(models.Post.likes),
            )
            .filter(models.Post.content.ilike(keyword))
            .order_by(models.Post.created_at.desc())
        )
        total_posts = post_query.count()
        posts_result = [
            _serialize_post(p, current_user.id)
            for p in post_query.offset(skip).limit(limit).all()
        ]

    return SearchResponse(
        users=users_result,
        posts=posts_result,
        total_users=total_users,
        total_posts=total_posts,
        query=q.strip(),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  GET /search/users  — user-only quick search (for chat new-conversation modal)
# ══════════════════════════════════════════════════════════════════════════════
@router.get(
    "/users",
    response_model=List[schemas.UserPublic],
    summary="Search users only (quick lookup)",
)
def search_users(
    q: str = Query(..., min_length=1, max_length=100),
    role: Optional[str] = Query(default=None, description="Filter by role: student | alumni"),
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Quick user search, optionally filtered by role.
    Excludes the current user from results.
    """
    keyword = f"%{q.strip()}%"
    query = db.query(models.User).filter(
        models.User.id != current_user.id,
        or_(
            models.User.name.ilike(keyword),
            models.User.skills.ilike(keyword),
            models.User.college.ilike(keyword),
        ),
    )
    if role in ("student", "alumni", "admin"):
        query = query.filter(models.User.role == role)

    return query.limit(limit).all()
