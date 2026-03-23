"""
Posts, Comments, Likes — with notifications wired in.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from .notification_routes import create_notification

router = APIRouter(tags=["Posts, Comments & Likes"])


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


def _load_post(post_id: int, db: Session) -> models.Post:
    post = (
        db.query(models.Post)
        .options(
            joinedload(models.Post.author),
            joinedload(models.Post.comments).joinedload(models.Comment.author),
            joinedload(models.Post.likes),
        )
        .filter(models.Post.id == post_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
    return post


# ══════════════════════════════════════════════════════════════════════════════
#  Posts
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/posts", response_model=schemas.PostOut, status_code=201,
             summary="Create a new post")
def create_post(
    payload: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = models.Post(
        user_id=current_user.id,
        content=payload.content,
        image_url=payload.image_url,
    )
    db.add(post)
    db.commit()
    return _serialize_post(_load_post(post.id, db), current_user.id)


@router.get("/posts", response_model=List[schemas.PostOut],
            summary="Get paginated feed (newest first)")
def get_feed(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    limit = min(limit, 50)
    posts = (
        db.query(models.Post)
        .options(
            joinedload(models.Post.author),
            joinedload(models.Post.comments).joinedload(models.Comment.author),
            joinedload(models.Post.likes),
        )
        .order_by(models.Post.created_at.desc())
        .offset(skip).limit(limit).all()
    )
    return [_serialize_post(p, current_user.id) for p in posts]


@router.get("/posts/user/{user_id}", response_model=List[schemas.PostOut],
            summary="Get posts by a specific user")
def get_posts_by_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not db.query(models.User).filter(models.User.id == user_id).first():
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    posts = (
        db.query(models.Post)
        .options(
            joinedload(models.Post.author),
            joinedload(models.Post.comments).joinedload(models.Comment.author),
            joinedload(models.Post.likes),
        )
        .filter(models.Post.user_id == user_id)
        .order_by(models.Post.created_at.desc())
        .all()
    )
    return [_serialize_post(p, current_user.id) for p in posts]


@router.delete("/posts/{post_id}", status_code=204, summary="Delete a post")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    db.delete(post)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  Comments
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/comments", response_model=schemas.CommentOut, status_code=201,
             summary="Add a comment to a post")
def create_comment(
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = db.query(models.Post).filter(models.Post.id == payload.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment = models.Comment(
        post_id=payload.post_id,
        user_id=current_user.id,
        content=payload.content,
    )
    db.add(comment)

    # Notify post author
    create_notification(
        db,
        user_id=post.user_id,
        type="comment",
        message=f"{current_user.name} commented on your post",
        actor_id=current_user.id,
        link=f"/dashboard.html",
    )

    db.commit()
    db.refresh(comment)
    # trigger lazy-load of author inside session
    _ = comment.author
    return comment


@router.delete("/comments/{comment_id}", status_code=204,
               summary="Delete a comment")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    db.delete(comment)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  Likes
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/likes", response_model=schemas.LikeToggleResponse,
             summary="Toggle like on a post")
def toggle_like(
    payload: schemas.LikeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = db.query(models.Post).filter(models.Post.id == payload.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = db.query(models.Like).filter(
        models.Like.post_id == payload.post_id,
        models.Like.user_id == current_user.id,
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        liked = False
    else:
        db.add(models.Like(post_id=payload.post_id, user_id=current_user.id))
        # Notify post author on like
        create_notification(
            db,
            user_id=post.user_id,
            type="like",
            message=f"{current_user.name} liked your post",
            actor_id=current_user.id,
            link=f"/dashboard.html",
        )
        db.commit()
        liked = True

    count = db.query(models.Like).filter(
        models.Like.post_id == payload.post_id
    ).count()
    return schemas.LikeToggleResponse(liked=liked, likes_count=count)
