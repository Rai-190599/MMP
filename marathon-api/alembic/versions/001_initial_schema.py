"""001 initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-30 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Create native PostgreSQL enum types                                  #
    # ------------------------------------------------------------------ #
    user_role = postgresql.ENUM(
        "participant", "organizer", "volunteer",
        name="user_role", create_type=False
    )
    user_role.create(op.get_bind(), checkfirst=True)

    registration_status = postgresql.ENUM(
        "registered", "approved", "participation_confirmed",
        "bib_collected", "finished_certified",
        name="registration_status", create_type=False
    )
    registration_status.create(op.get_bind(), checkfirst=True)

    notification_channel = postgresql.ENUM(
        "email", "sms", "whatsapp",
        name="notification_channel", create_type=False
    )
    notification_channel.create(op.get_bind(), checkfirst=True)

    notification_trigger_type = postgresql.ENUM(
        "status_change", "manual_broadcast",
        name="notification_trigger_type", create_type=False
    )
    notification_trigger_type.create(op.get_bind(), checkfirst=True)

    task_category = postgresql.ENUM(
        "sponsors", "tshirt", "bib", "volunteers", "logistics",
        name="task_category", create_type=False
    )
    task_category.create(op.get_bind(), checkfirst=True)

    task_status = postgresql.ENUM(
        "todo", "in_progress", "done",
        name="task_status", create_type=False
    )
    task_status.create(op.get_bind(), checkfirst=True)

    volunteer_role_type = postgresql.ENUM(
        "registration_desk", "finish_line", "general",
        name="volunteer_role_type", create_type=False
    )
    volunteer_role_type.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------ #
    # users                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM(
                "participant", "organizer", "volunteer",
                name="user_role", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------ #
    # events                                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("distances", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sponsor_tiers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("faq", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # registrations                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "registered", "approved", "participation_confirmed",
                "bib_collected", "finished_certified",
                name="registration_status", create_type=False
            ),
            nullable=False,
            server_default="registered",
        ),
        sa.Column("distance", sa.String(20), nullable=True),
        sa.Column("tshirt_size", sa.String(10), nullable=True),
        sa.Column("emergency_contact", sa.String(255), nullable=True),
        sa.Column("bib_number", sa.String(20), nullable=True),
        sa.Column("qr_code_url", sa.Text(), nullable=True),
        sa.Column("finish_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certificate_url", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bib_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bib_number"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_registration_event_user"),
    )

    # ------------------------------------------------------------------ #
    # notifications                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("registration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "channel",
            postgresql.ENUM(
                "email", "sms", "whatsapp",
                name="notification_channel", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "trigger_type",
            postgresql.ENUM(
                "status_change", "manual_broadcast",
                name="notification_trigger_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # tasks                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "sponsors", "tshirt", "bib", "volunteers", "logistics",
                name="task_category", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "todo", "in_progress", "done",
                name="task_status", create_type=False
            ),
            nullable=False,
            server_default="todo",
        ),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column(
            "checklist",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # volunteer_assignments                                                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        "volunteer_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role_type",
            postgresql.ENUM(
                "registration_desk", "finish_line", "general",
                name="volunteer_role_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_volunteer_assignment_event_user"),
    )


def downgrade() -> None:
    op.drop_table("volunteer_assignments")
    op.drop_table("tasks")
    op.drop_table("notifications")
    op.drop_table("registrations")
    op.drop_table("events")
    op.drop_table("users")

    # Drop enum types
    for enum_name in [
        "volunteer_role_type",
        "task_status",
        "task_category",
        "notification_trigger_type",
        "notification_channel",
        "registration_status",
        "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
