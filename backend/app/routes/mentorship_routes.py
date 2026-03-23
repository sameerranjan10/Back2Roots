"""
Mentorship request workflow — with notifications on every state change.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from .notification_routes import create_notification

router = APIRouter(prefix="/mentorship", tags=["Mentorship"])


@router.post("", response_model=schemas.MentorshipOut, status_code=201,
             summary="Send a mentorship request to an alumni")
def send_request(
    payload: schemas.MentorshipCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Students only. Duplicate pending requests to the same alumni are rejected."""
    if current_user.role not in ("student", "admin"):
        raise HTTPException(status_code=403, detail="Only students can send mentorship requests")

    alumni = db.query(models.User).filter(
        models.User.id == payload.alumni_id,
        models.User.role == "alumni",
    ).first()
    if not alumni:
        raise HTTPException(status_code=404, detail=f"Alumni {payload.alumni_id} not found")

    duplicate = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.student_id == current_user.id,
        models.MentorshipRequest.alumni_id  == payload.alumni_id,
        models.MentorshipRequest.status     == "pending",
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="You already have a pending request with this alumni")

    req = models.MentorshipRequest(
        student_id=current_user.id,
        alumni_id=payload.alumni_id,
        message=payload.message,
    )
    db.add(req)

    # Notify the alumni
    create_notification(
        db,
        user_id=payload.alumni_id,
        type="mentorship_request",
        message=f"{current_user.name} sent you a mentorship request",
        actor_id=current_user.id,
        link="/dashboard.html#mentorship",
    )

    db.commit()
    db.refresh(req)
    return req


@router.put("/{request_id}", response_model=schemas.MentorshipOut,
            summary="Accept or reject a mentorship request")
def respond_to_request(
    request_id: int,
    payload: schemas.MentorshipUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Alumni only (or admin). Only pending requests can be updated."""
    req = db.query(models.MentorshipRequest).filter(
        models.MentorshipRequest.id == request_id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.alumni_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to respond to this request")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already '{req.status}'")

    req.status = payload.status.value

    # Notify the student
    verb = "accepted" if payload.status.value == "accepted" else "declined"
    create_notification(
        db,
        user_id=req.student_id,
        type="mentorship_update",
        message=f"{current_user.name} {verb} your mentorship request",
        actor_id=current_user.id,
        link="/dashboard.html#mentorship",
    )

    db.commit()
    db.refresh(req)
    return req


@router.get("/pending", response_model=List[schemas.MentorshipOut],
            summary="Get pending mentorship requests (alumni view)")
def get_pending(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "alumni":
        raise HTTPException(status_code=403, detail="Only alumni can access this endpoint")
    return (
        db.query(models.MentorshipRequest)
        .filter(
            models.MentorshipRequest.alumni_id == current_user.id,
            models.MentorshipRequest.status    == "pending",
        )
        .order_by(models.MentorshipRequest.created_at.desc())
        .all()
    )


@router.get("/my-requests", response_model=List[schemas.MentorshipOut],
            summary="Get my mentorship requests (role-aware)")
def get_my_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.MentorshipRequest)
    if current_user.role == "student":
        q = q.filter(models.MentorshipRequest.student_id == current_user.id)
    elif current_user.role == "alumni":
        q = q.filter(models.MentorshipRequest.alumni_id  == current_user.id)
    # admin: no filter — sees all
    return q.order_by(models.MentorshipRequest.created_at.desc()).all()
