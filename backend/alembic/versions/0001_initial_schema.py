"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),     nullable=False),
        sa.Column("name",            sa.String(100),   nullable=False),
        sa.Column("email",           sa.String(150),   nullable=False),
        sa.Column("password",        sa.String(255),   nullable=False),
        sa.Column("role",            sa.Enum("student","alumni","admin"), nullable=False, server_default="student"),
        sa.Column("college",         sa.String(200),   nullable=True),
        sa.Column("skills",          sa.Text(),        nullable=True),
        sa.Column("bio",             sa.Text(),        nullable=True),
        sa.Column("profile_picture", sa.String(500),   nullable=True),
        sa.Column("created_at",      sa.DateTime(),    nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id",    "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── posts ──────────────────────────────────────────────────────────────────
    op.create_table(
        "posts",
        sa.Column("id",        sa.Integer(), nullable=False),
        sa.Column("user_id",   sa.Integer(), nullable=False),
        sa.Column("content",   sa.Text(),    nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("created_at",sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_posts_id",      "posts", ["id"])
    op.create_index("ix_posts_user_id", "posts", ["user_id"])

    # ── comments ───────────────────────────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id",        sa.Integer(), nullable=False),
        sa.Column("post_id",   sa.Integer(), nullable=False),
        sa.Column("user_id",   sa.Integer(), nullable=False),
        sa.Column("content",   sa.Text(),    nullable=False),
        sa.Column("created_at",sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_id",      "comments", ["id"])
    op.create_index("ix_comments_post_id", "comments", ["post_id"])

    # ── likes ──────────────────────────────────────────────────────────────────
    op.create_table(
        "likes",
        sa.Column("id",      sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id","user_id", name="uq_post_user_like"),
    )
    op.create_index("ix_likes_id", "likes", ["id"])

    # ── messages ───────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id",          sa.Integer(),    nullable=False),
        sa.Column("sender_id",   sa.Integer(),    nullable=False),
        sa.Column("receiver_id", sa.Integer(),    nullable=False),
        sa.Column("content",     sa.Text(),       nullable=False),
        sa.Column("is_read",     sa.Boolean(),    nullable=True, server_default="0"),
        sa.Column("created_at",  sa.DateTime(),   nullable=True),
        sa.ForeignKeyConstraint(["sender_id"],   ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_id",          "messages", ["id"])
    op.create_index("ix_messages_sender_id",   "messages", ["sender_id"])
    op.create_index("ix_messages_receiver_id", "messages", ["receiver_id"])

    # ── mentorship_requests ────────────────────────────────────────────────────
    op.create_table(
        "mentorship_requests",
        sa.Column("id",         sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("alumni_id",  sa.Integer(), nullable=False),
        sa.Column("status",     sa.Enum("pending","accepted","rejected"), nullable=False, server_default="pending"),
        sa.Column("message",    sa.Text(),    nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alumni_id"],  ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mentorship_id",         "mentorship_requests", ["id"])
    op.create_index("ix_mentorship_student_id", "mentorship_requests", ["student_id"])
    op.create_index("ix_mentorship_alumni_id",  "mentorship_requests", ["alumni_id"])

    # ── notifications ──────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id",         sa.Integer(),  nullable=False),
        sa.Column("user_id",    sa.Integer(),  nullable=False),
        sa.Column("actor_id",   sa.Integer(),  nullable=True),
        sa.Column("type",       sa.Enum("like","comment","mentorship_request","mentorship_update",
                                        "message","system", name="notification_type"), nullable=False),
        sa.Column("message",    sa.Text(),     nullable=False),
        sa.Column("link",       sa.String(500), nullable=True),
        sa.Column("is_read",    sa.Boolean(),  nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"],  ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_id",      "notifications", ["id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("mentorship_requests")
    op.drop_table("messages")
    op.drop_table("likes")
    op.drop_table("comments")
    op.drop_table("posts")
    op.drop_table("users")
    # Drop the notification_type enum on Postgres; MySQL ignores this
    try:
        sa.Enum(name="notification_type").drop(op.get_bind())
    except Exception:
        pass
