"""Single user refactor - No-op migration.

Revision ID: 20251126_single_user
Revises: 005_add_participant_metadata
Create Date: 2025-11-26 10:00:00.000000

This migration is marked as no-op since all schema was created
by the initial migration. This file serves as a placeholder in the
migration chain to maintain compatibility.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251126_single_user"
down_revision = "005_add_participant_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op upgrade. All schema already created by initial migration."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
