"""add job summary brief source

Revision ID: 5aa8b3db4f5e
Revises: f4b19be77f6d
Create Date: 2026-05-10 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "5aa8b3db4f5e"
down_revision = "f4b19be77f6d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("summary_brief_source", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_column("summary_brief_source")
