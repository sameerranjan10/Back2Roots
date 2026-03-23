import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models
from .database import get_db

# ─── Configuration ─────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv(
    "SECRET_KEY",
    "alumni-nexus-super-secret-key-change-me-in-production-2024!"
)
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TOKEN_EXPIRE_MINUTES", "1440"))  # 24 h

# ─── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# ─── OAuth2 bearer scheme ──────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ══════════════════════════════════════════════════════════════════════════════
#  Password helpers
# ══════════════════════════════════════════════════════════════════════════════
def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return pwd_context.verify(plain, hashed)


def get_password_hash(plain: str) -> str:
    """Return bcrypt hash of *plain*."""
    return pwd_context.hash(plain)


# ══════════════════════════════════════════════════════════════════════════════
#  JWT helpers
# ══════════════════════════════════════════════════════════════════════════════
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create and return a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[int]:
    """Decode *token* and return user_id (sub) or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (JWTError, ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  FastAPI Dependencies
# ══════════════════════════════════════════════════════════════════════════════
_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Dependency — resolves the Bearer token to the authenticated User row.
    Raises HTTP 401 if token is invalid or user not found.
    """
    user_id = _decode_token(token)
    if user_id is None:
        raise _401

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise _401
    return user


def require_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Dependency — ensures the current user is an admin.
    Raises HTTP 403 otherwise.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user
