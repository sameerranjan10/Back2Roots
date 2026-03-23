"""
File upload endpoints.

POST /upload/avatar       — upload profile picture (multipart)
POST /upload/post-image   — upload an image for a post (multipart)

Files are saved to ./uploads/ on the server and served at /static/uploads/.
In production, swap the local save logic for S3 / Cloudinary / any CDN.
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from .. import models

router = APIRouter(prefix="/upload", tags=["File Upload"])

# ── Storage config ─────────────────────────────────────────────────────────────
UPLOAD_DIR   = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

AVATAR_DIR   = UPLOAD_DIR / "avatars"
IMAGES_DIR   = UPLOAD_DIR / "post_images"
AVATAR_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class UploadResponse(BaseModel):
    url:      str
    filename: str
    size:     int


def _validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. "
                   f"Allowed: jpeg, png, gif, webp",
        )


def _save_file(file: UploadFile, directory: Path) -> tuple[str, int]:
    """Save uploaded file with a UUID filename. Returns (filename, size_bytes)."""
    ext      = Path(file.filename or "image").suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest     = directory / filename

    size = 0
    with open(dest, "wb") as f:
        while chunk := file.file.read(1024 * 64):   # 64KB chunks
            size += len(chunk)
            if size > MAX_FILE_SIZE_BYTES:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File too large. Maximum size is 5 MB.",
                )
            f.write(chunk)

    return filename, size


# ══════════════════════════════════════════════════════════════════════════════
#  POST /upload/avatar
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/avatar",
    response_model=UploadResponse,
    summary="Upload a profile picture",
)
def upload_avatar(
    file: UploadFile = File(..., description="Profile picture (JPEG/PNG/GIF/WebP, max 5 MB)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload a profile picture.

    - Accepts: JPEG, PNG, GIF, WebP
    - Max size: 5 MB
    - Automatically updates the user's `profile_picture` URL
    - Deletes the previous avatar file if it was locally stored

    Returns the public URL of the uploaded file.
    """
    _validate_image(file)
    filename, size = _save_file(file, AVATAR_DIR)

    # Delete old avatar if it was a local upload
    if current_user.profile_picture:
        old_path = Path(current_user.profile_picture.lstrip("/"))
        if old_path.exists() and str(old_path).startswith("uploads"):
            old_path.unlink(missing_ok=True)

    url = f"/static/uploads/avatars/{filename}"
    current_user.profile_picture = url
    db.commit()

    return UploadResponse(url=url, filename=filename, size=size)


# ══════════════════════════════════════════════════════════════════════════════
#  POST /upload/post-image
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/post-image",
    response_model=UploadResponse,
    summary="Upload an image for a post",
)
def upload_post_image(
    file: UploadFile = File(..., description="Post image (JPEG/PNG/GIF/WebP, max 5 MB)"),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload an image to attach to a new post.

    Returns the public URL — include this as `image_url` when calling
    `POST /posts`.
    """
    _validate_image(file)
    filename, size = _save_file(file, IMAGES_DIR)
    url = f"/static/uploads/post_images/{filename}"
    return UploadResponse(url=url, filename=filename, size=size)
