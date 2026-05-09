"""add job summary brief column

Revision ID: f4b19be77f6d
Revises: e1a9f3b2d114
Create Date: 2026-05-09 22:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f4b19be77f6d"
down_revision = "e1a9f3b2d114"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("summary_brief", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_column("summary_brief")
