"""002 sprint0 additions: admin role, organizer_invites, event_organizers

Revision ID: 002
Revises: 001
Create Date: 2026-06-01 00:00:00.000000

NOTE: PostgreSQL does not support removing enum values, so downgrade cannot
undo the 'admin' addition to user_role. The downgrade only drops the new tables.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add 'admin' to user_role enum.
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction in PostgreSQL.
    # With asyncpg the connection is already inside a transaction started by
    # Alembic, so we use the underlying psycopg2-style escape hatch:
    # execute the statement via the raw DBAPI connection in autocommit mode.
    conn = op.get_bind()
    # conn.connection is the psycopg2 connection (via asyncpg sync wrapper)
    # For asyncpg-backed connections we use execute() with COMMIT trick instead.
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin'"))
    conn.execute(sa.text("BEGIN"))

    op.create_table(
        "organizer_invites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "token",
            postgresql.UUID(as_uuid=True),
            unique=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "event_organizers",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "user_id"),
    )


def downgrade() -> None:
    # NOTE: 'admin' value cannot be removed from user_role enum in PostgreSQL.
    op.drop_table("event_organizers")
    op.drop_table("organizer_invites")
