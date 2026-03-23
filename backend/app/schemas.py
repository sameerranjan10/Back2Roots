from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from enum import Enum as PyEnum

from pydantic import BaseModel, EmailStr, field_validator, model_validator


# ══════════════════════════════════════════════════════════════════════════════
#  Shared Enums
# ══════════════════════════════════════════════════════════════════════════════
class RoleEnum(str, PyEnum):
    student = "student"
    alumni  = "alumni"
    admin   = "admin"


class MentorshipStatusEnum(str, PyEnum):
    pending  = "pending"
    accepted = "accepted"
    rejected = "rejected"


# ══════════════════════════════════════════════════════════════════════════════
#  User Schemas
# ══════════════════════════════════════════════════════════════════════════════
class UserCreate(BaseModel):
    name:     str
    email:    EmailStr
    password: str
    role:     RoleEnum          = RoleEnum.student
    college:  Optional[str]     = None
    skills:   Optional[str]     = None
    bio:      Optional[str]     = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) > 100:
            raise ValueError("Name too long (max 100 chars)")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLogin(BaseModel):
    email:    EmailStr
    password: str


class UserUpdate(BaseModel):
    name:            Optional[str] = None
    bio:             Optional[str] = None
    skills:          Optional[str] = None
    college:         Optional[str] = None
    profile_picture: Optional[str] = None


class UserPublic(BaseModel):
    """Minimal user info safe to embed in posts, comments, etc."""
    id:              int
    name:            str
    role:            str
    college:         Optional[str] = None
    skills:          Optional[str] = None
    bio:             Optional[str] = None
    profile_picture: Optional[str] = None

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    """Full user object returned to the owner / admin."""
    id:              int
    name:            str
    email:           str
    role:            str
    college:         Optional[str] = None
    skills:          Optional[str] = None
    bio:             Optional[str] = None
    profile_picture: Optional[str] = None
    created_at:      datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
#  Auth / Token
# ══════════════════════════════════════════════════════════════════════════════
class Token(BaseModel):
    access_token: str
    token_type:   str
    user:         UserOut


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ══════════════════════════════════════════════════════════════════════════════
#  Post Schemas
# ══════════════════════════════════════════════════════════════════════════════
class PostCreate(BaseModel):
    content:   str
    image_url: Optional[str] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Post content cannot be empty")
        return v


class CommentCreate(BaseModel):
    post_id: int
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Comment cannot be empty")
        return v


class CommentOut(BaseModel):
    id:         int
    post_id:    int
    user_id:    int
    content:    str
    created_at: datetime
    author:     UserPublic

    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id:           int
    user_id:      int
    content:      str
    image_url:    Optional[str] = None
    created_at:   datetime
    author:       UserPublic
    comments:     List[CommentOut] = []
    likes_count:  int              = 0
    liked_by_me:  bool             = False

    model_config = {"from_attributes": True}


class LikeCreate(BaseModel):
    post_id: int


class LikeToggleResponse(BaseModel):
    liked:       bool
    likes_count: int


# ══════════════════════════════════════════════════════════════════════════════
#  Message Schemas
# ══════════════════════════════════════════════════════════════════════════════
class MessageCreate(BaseModel):
    receiver_id: int
    content:     str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message content cannot be empty")
        return v


class MessageOut(BaseModel):
    id:          int
    sender_id:   int
    receiver_id: int
    content:     str
    is_read:     bool
    created_at:  datetime

    model_config = {"from_attributes": True}


class ConversationPartner(BaseModel):
    user:         UserPublic
    last_message: Optional[str] = None
    unread_count: int           = 0


# ══════════════════════════════════════════════════════════════════════════════
#  Mentorship Schemas
# ══════════════════════════════════════════════════════════════════════════════
class MentorshipCreate(BaseModel):
    alumni_id: int
    message:   Optional[str] = None


class MentorshipUpdate(BaseModel):
    status: MentorshipStatusEnum


class MentorshipOut(BaseModel):
    id:         int
    student_id: int
    alumni_id:  int
    status:     str
    message:    Optional[str] = None
    created_at: datetime
    student:    UserPublic
    alumni:     UserPublic

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
#  AI Schemas
# ══════════════════════════════════════════════════════════════════════════════
class ChatbotRequest(BaseModel):
    message: str


class ChatbotResponse(BaseModel):
    reply:       str
    suggestions: List[UserPublic] = []


class RecommendationOut(BaseModel):
    user:   UserPublic
    score:  float
    reason: str


# ══════════════════════════════════════════════════════════════════════════════
#  Generic
# ══════════════════════════════════════════════════════════════════════════════
class MessageResponse(BaseModel):
    message: str
