from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    Boolean, ForeignKey, Enum, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from .database import Base


# ══════════════════════════════════════════════════════════════════════════════
#  User
# ══════════════════════════════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(100),  nullable=False)
    email            = Column(String(150),  unique=True, index=True, nullable=False)
    password         = Column(String(255),  nullable=False)
    role             = Column(Enum("student", "alumni", "admin"), default="student", nullable=False)
    college          = Column(String(200))
    skills           = Column(Text)          # comma-separated, e.g. "Python, Django, ML"
    bio              = Column(Text)
    profile_picture  = Column(String(500))
    created_at       = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────────
    posts = relationship(
        "Post", back_populates="author",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "Comment", back_populates="author",
        cascade="all, delete-orphan",
    )
    likes = relationship(
        "Like", back_populates="user",
        cascade="all, delete-orphan",
    )
    sent_messages = relationship(
        "Message", foreign_keys="Message.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan",
    )
    received_messages = relationship(
        "Message", foreign_keys="Message.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan",
    )
    mentorship_as_student = relationship(
        "MentorshipRequest", foreign_keys="MentorshipRequest.student_id",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    mentorship_as_alumni = relationship(
        "MentorshipRequest", foreign_keys="MentorshipRequest.alumni_id",
        back_populates="alumni",
        cascade="all, delete-orphan",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Post
# ══════════════════════════════════════════════════════════════════════════════
class Post(Base):
    __tablename__ = "posts"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content    = Column(Text, nullable=False)
    image_url  = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    author   = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes    = relationship("Like",    back_populates="post", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════════════════════════
#  Comment
# ══════════════════════════════════════════════════════════════════════════════
class Comment(Base):
    __tablename__ = "comments"

    id         = Column(Integer, primary_key=True, index=True)
    post_id    = Column(Integer, ForeignKey("posts.id",  ondelete="CASCADE"), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id",  ondelete="CASCADE"), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post   = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")


# ══════════════════════════════════════════════════════════════════════════════
#  Like  (unique per user per post)
# ══════════════════════════════════════════════════════════════════════════════
class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_user_like"),
    )

    id      = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id",  ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id",  ondelete="CASCADE"), nullable=False)

    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")


# ══════════════════════════════════════════════════════════════════════════════
#  Message
# ══════════════════════════════════════════════════════════════════════════════
class Message(Base):
    __tablename__ = "messages"

    id          = Column(Integer, primary_key=True, index=True)
    sender_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content     = Column(Text, nullable=False)
    is_read     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    sender   = relationship("User", foreign_keys=[sender_id],   back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")


# ══════════════════════════════════════════════════════════════════════════════
#  MentorshipRequest
# ══════════════════════════════════════════════════════════════════════════════
class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alumni_id  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status     = Column(Enum("pending", "accepted", "rejected"), default="pending", nullable=False)
    message    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id], back_populates="mentorship_as_student")
    alumni  = relationship("User", foreign_keys=[alumni_id],  back_populates="mentorship_as_alumni")
