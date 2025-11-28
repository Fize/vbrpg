"""Add game_roles table

Revision ID: 20251128_0006_add_game_roles
Revises: 20251126_single_user
Create Date: 2025-11-28 00:06:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251128_0006_add_game_roles"
down_revision = "20251126_single_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("game_type_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("is_playable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_type_id"], ["game_types.id"], ondelete="CASCADE")
    )


def downgrade() -> None:
    op.drop_table("game_roles")
