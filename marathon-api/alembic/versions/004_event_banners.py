"""004 event banners: add banner_images JSONB column to events

Revision ID: 004
Revises: 003
Create Date: 2026-06-01 00:00:00.000000

Adds a JSONB array column to store MinIO object names for event banner images.
e.g. ["banners/event-id/1.jpg", "banners/event-id/2.jpg"]
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "banner_images",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "banner_images")
