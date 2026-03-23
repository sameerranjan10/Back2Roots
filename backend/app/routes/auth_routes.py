"""
Authentication routes — register, login, forgot/reset password.

Rate limiting applied to prevent brute-force attacks.
College email domain validation enforced when COLLEGE_DOMAINS is configured.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import (
    get_current_user,
    get_password_hash,
    verify_password,
    create_access_token,
)
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── In-memory reset token store (use Redis in production) ─────────────────────
_reset_tokens: dict = {}
RESET_TOKEN_EXPIRE_MINUTES = 30

# ── College domain whitelist (empty = all domains accepted) ────────────────────
COLLEGE_DOMAINS: list = [
    # e.g. "iitb.ac.in", "iitd.ac.in"
]

# ── Rate limit store ──────────────────────────────────────────────────────────
_login_attempts: dict = {}
_MAX_ATTEMPTS   = 10
_WINDOW_SECONDS = 300   # 5 minutes


# ── Extra schemas ─────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message:     str
    reset_token: Optional[str] = None   # returned only in DEBUG mode

class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_college_email(email: str) -> None:
    if not COLLEGE_DOMAINS:
        return
    domain = email.lower().split("@")[-1]
    if domain not in [d.lower() for d in COLLEGE_DOMAINS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration restricted to: {', '.join(COLLEGE_DOMAINS)}",
        )


def _check_rate_limit(key: str) -> None:
    now    = datetime.utcnow()
    cutoff = now - timedelta(seconds=_WINDOW_SECONDS)
    attempts = [t for t in _login_attempts.get(key, []) if t > cutoff]
    _login_attempts[key] = attempts
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Wait {_WINDOW_SECONDS // 60} minutes.",
        )
    attempts.append(now)
    _login_attempts[key] = attempts


def _clear_rate_limit(key: str) -> None:
    _login_attempts.pop(key, None)


# ══════════════════════════════════════════════════════════════════════════════
#  POST /auth/register
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/register",
    response_model=schemas.Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student or alumni account",
)
def register(payload: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    """
    Create a new account.

    - College email validation applied when COLLEGE_DOMAINS is configured.
    - Admin accounts cannot be created via this endpoint (use CLI).
    - Returns a JWT token immediately so the user is logged in after registration.
    """
    _validate_college_email(payload.email)

    if payload.role.value == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts cannot be created via registration. Use the CLI.",
        )

    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    user = models.User(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        password=get_password_hash(payload.password),
        role=payload.role.value,
        college=payload.college,
        skills=payload.skills,
        bio=payload.bio,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return schemas.Token(
        access_token=token,
        token_type="bearer",
        user=schemas.UserOut.model_validate(user),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  POST /auth/login
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/login",
    response_model=schemas.Token,
    summary="Login and receive a JWT access token",
)
def login(credentials: schemas.UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    Authenticate with email + password.

    Rate-limited: 10 attempts per 5 minutes per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = db.query(models.User).filter(
        models.User.email == credentials.email.lower().strip()
    ).first()

    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    _clear_rate_limit(client_ip)
    token = create_access_token({"sub": str(user.id)})
    return schemas.Token(
        access_token=token,
        token_type="bearer",
        user=schemas.UserOut.model_validate(user),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  POST /auth/forgot-password
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request a password reset token",
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Generate a time-limited password reset token.

    Always returns HTTP 200 to prevent email enumeration.
    In DEBUG mode, the token is returned in the response body.
    In production, integrate with an email service (SendGrid, SES, etc.).
    """
    user = db.query(models.User).filter(
        models.User.email == payload.email.lower().strip()
    ).first()

    msg = ForgotPasswordResponse(message="If that email exists, a reset link has been sent.")

    if not user:
        return msg   # don't reveal whether email exists

    token = secrets.token_urlsafe(32)
    _reset_tokens[token] = {
        "user_id": user.id,
        "expires": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    }

    # TODO production: send_reset_email(user.email, token)

    if settings.DEBUG:
        msg.reset_token = token   # expose in dev only

    return msg


# ══════════════════════════════════════════════════════════════════════════════
#  POST /auth/reset-password
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/reset-password",
    response_model=schemas.MessageResponse,
    summary="Reset password using a reset token",
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Complete a password reset using the token from forgot-password.

    Tokens are single-use and expire after 30 minutes.
    """
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    record = _reset_tokens.get(payload.token)
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if datetime.utcnow() > record["expires"]:
        _reset_tokens.pop(payload.token, None)
        raise HTTPException(status_code=400, detail="Reset token has expired")

    user = db.query(models.User).filter(models.User.id == record["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = get_password_hash(payload.new_password)
    db.commit()
    _reset_tokens.pop(payload.token, None)   # single-use

    return schemas.MessageResponse(message="Password reset successfully. You can now log in.")


# ══════════════════════════════════════════════════════════════════════════════
#  POST /auth/change-password  (authenticated)
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/change-password",
    response_model=schemas.MessageResponse,
    summary="Change password (requires current password)",
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Change password for the currently authenticated user."""
    if not verify_password(payload.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=422, detail="New password must be at least 6 characters")

    current_user.password = get_password_hash(payload.new_password)
    db.commit()
    return schemas.MessageResponse(message="Password changed successfully.")
