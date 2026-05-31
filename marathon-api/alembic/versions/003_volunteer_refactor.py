"""003 volunteer refactor: remove volunteer from user_role, add volunteer_applications, add slot_caps

Revision ID: 003
Revises: 002
Create Date: 2026-06-01 00:00:00.000000

Removes 'volunteer' from the user_role enum (volunteer identity is now expressed
via volunteer_assignments / volunteer_applications, not a permanent user role).
Adds volunteer_slot_caps JSONB column to events.
Creates volunteer_applications table.

PostgreSQL does not support DROP VALUE on an enum, so we recreate the type:
  1. Create user_role_new without 'volunteer'
  2. ALTER COLUMN to use new type (USING cast)
  3. DROP old type
  4. RENAME new type to user_role
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1 — Safety gate: abort if any volunteer users exist
    # ------------------------------------------------------------------
    result = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'volunteer'"))
    count = result.scalar()
    if count > 0:
        raise Exception(
            f"{count} user(s) have role='volunteer'. "
            "Reassign them to 'participant' before running this migration:\n"
            "  UPDATE users SET role='participant' WHERE role='volunteer';"
        )

    # ------------------------------------------------------------------
    # Step 2 — Replace user_role enum (recreate without 'volunteer')
    # ALTER TYPE ... DROP VALUE is not supported in PostgreSQL, so we
    # create a new enum, alter the column, drop the old one, then rename.
    # These DDL statements must run outside a transaction block.
    # ------------------------------------------------------------------
    conn.execute(text("COMMIT"))

    conn.execute(text(
        "CREATE TYPE user_role_new AS ENUM ('participant', 'organizer', 'admin')"
    ))

    conn.execute(text("BEGIN"))

    conn.execute(text(
        "ALTER TABLE users "
        "ALTER COLUMN role TYPE user_role_new "
        "USING role::text::user_role_new"
    ))

    conn.execute(text("DROP TYPE user_role"))
    conn.execute(text("ALTER TYPE user_role_new RENAME TO user_role"))

    # ------------------------------------------------------------------
    # Step 3 — Add volunteer_slot_caps to events
    # ------------------------------------------------------------------
    op.add_column(
        "events",
        sa.Column(
            "volunteer_slot_caps",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text(
                '\'{"registration_desk": 5, "finish_line": 3, "general": 10}\'::jsonb'
            ),
        ),
    )

    # ------------------------------------------------------------------
    # Step 4 — Create volunteer_applications table
    # ------------------------------------------------------------------
    op.create_table(
        "volunteer_applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 'registration_desk' | 'finish_line' | 'general'
        sa.Column("desired_role", sa.String(50), nullable=False),
        # 'pending' | 'approved' | 'rejected'
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "event_id", "user_id", name="uq_volunteer_application_event_user"
        ),
    )


def downgrade() -> None:
    # Drop new table and column first
    op.drop_table("volunteer_applications")
    op.drop_column("events", "volunteer_slot_caps")

    # Restore user_role enum with 'volunteer' value
    conn = op.get_bind()

    conn.execute(text("COMMIT"))
    conn.execute(text(
        "CREATE TYPE user_role_old AS ENUM ('participant', 'organizer', 'volunteer', 'admin')"
    ))
    conn.execute(text("BEGIN"))

    conn.execute(text(
        "ALTER TABLE users "
        "ALTER COLUMN role TYPE user_role_old "
        "USING role::text::user_role_old"
    ))

    conn.execute(text("DROP TYPE user_role"))
    conn.execute(text("ALTER TYPE user_role_old RENAME TO user_role"))
