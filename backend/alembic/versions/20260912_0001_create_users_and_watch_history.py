"""Первая миграция: таблицы users и watch_history.

Revision ID: 0001
Revises:
Create Date: 2026-09-12

"""

import sqlalchemy as sa
from alembic import op

# Идентификаторы версий
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "watch_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("channel_title", sa.String(length=255), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=False),
        sa.Column(
            "watched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_watch_history")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_watch_history_user_id_users"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("ix_watch_history_user_id"), "watch_history", ["user_id"])
    op.create_index(
        "ix_watch_history_user_watched", "watch_history", ["user_id", "watched_at"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_watch_history_user_id"), table_name="watch_history")
    op.drop_index("ix_watch_history_user_watched", table_name="watch_history")
    op.drop_table("watch_history")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")