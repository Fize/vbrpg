"""Add participant metadata placeholder migration.

Revision ID: 005_add_participant_metadata
Revises: 001_initial
Create Date: 2025-11-30

This is a safe no-op placeholder migration to fill a missing revision
that some later migrations reference. It intentionally performs no
schema changes so it won't modify existing databases.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "005_add_participant_metadata"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op upgrade: placeholder to satisfy revision chain.
    """
    # Intentionally empty. This revision is a stitching migration to
    # connect existing revision graph where the original '005' file
    # is missing from the repository.
    pass


def downgrade() -> None:
    """No-op downgrade"""
    pass
