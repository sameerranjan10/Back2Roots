from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..auth import get_current_user, require_admin
from ..database import get_db

router = APIRouter(prefix="/users", tags=["Users"])


# ══════════════════════════════════════════════════════════════════════════════
#  Current user — GET /users/me  &  PUT /users/me
# ══════════════════════════════════════════════════════════════════════════════
@router.get(
    "/me",
    response_model=schemas.UserOut,
    summary="Get my profile",
)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Return the full profile of the currently authenticated user."""
    return current_user


@router.put(
    "/me",
    response_model=schemas.UserOut,
    summary="Update my profile",
)
def update_me(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update editable profile fields of the current user.

    All fields are optional — only provided fields are updated.
    """
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


# ══════════════════════════════════════════════════════════════════════════════
#  Alumni & Students lists
# ══════════════════════════════════════════════════════════════════════════════
@router.get(
    "/alumni",
    response_model=List[schemas.UserPublic],
    summary="List all alumni",
)
def list_alumni(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Return all users with role = alumni."""
    return db.query(models.User).filter(models.User.role == "alumni").all()


@router.get(
    "/students",
    response_model=List[schemas.UserPublic],
    summary="List all students",
)
def list_students(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Return all users with role = student."""
    return db.query(models.User).filter(models.User.role == "student").all()


# ══════════════════════════════════════════════════════════════════════════════
#  Admin — list & delete all users
# (These routes must appear BEFORE /{user_id} to avoid route shadowing)
# ══════════════════════════════════════════════════════════════════════════════
@router.get(
    "/",
    response_model=List[schemas.UserOut],
    summary="[Admin] List all users",
)
def admin_list_all_users(
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    """**Admin only.** Return every user in the system."""
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


# ══════════════════════════════════════════════════════════════════════════════
#  Public user profile  — GET /users/{user_id}
# ══════════════════════════════════════════════════════════════════════════════
@router.get(
    "/{user_id}",
    response_model=schemas.UserPublic,
    summary="Get a user's public profile",
)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Return the public profile of any user by their ID."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user


# ══════════════════════════════════════════════════════════════════════════════
#  Admin — DELETE /users/{user_id}
# ══════════════════════════════════════════════════════════════════════════════
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Admin] Delete a user",
)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    """
    **Admin only.** Permanently delete a user and all associated content
    (posts, comments, likes, messages, mentorship requests) via cascade.
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own admin account",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    db.delete(user)
    db.commit()
    # 204 — no body returned
