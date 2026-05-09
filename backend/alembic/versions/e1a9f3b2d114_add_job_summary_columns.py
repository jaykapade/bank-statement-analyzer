"""add job summary columns

Revision ID: e1a9f3b2d114
Revises: c2d8e4f1b7a9
Create Date: 2026-05-09 22:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e1a9f3b2d114"
down_revision = "c2d8e4f1b7a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(
            sa.Column("summary_transaction_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("summary_income_total", sa.Numeric(18, 2), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("summary_expense_total", sa.Numeric(18, 2), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("summary_net_total", sa.Numeric(18, 2), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("summary_done_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("summary_pending_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("summary_failed_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("summary_last_computed_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column("summary_transaction_count", server_default=None)
        batch_op.alter_column("summary_income_total", server_default=None)
        batch_op.alter_column("summary_expense_total", server_default=None)
        batch_op.alter_column("summary_net_total", server_default=None)
        batch_op.alter_column("summary_done_count", server_default=None)
        batch_op.alter_column("summary_pending_count", server_default=None)
        batch_op.alter_column("summary_failed_count", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_column("summary_last_computed_at")
        batch_op.drop_column("summary_failed_count")
        batch_op.drop_column("summary_pending_count")
        batch_op.drop_column("summary_done_count")
        batch_op.drop_column("summary_net_total")
        batch_op.drop_column("summary_expense_total")
        batch_op.drop_column("summary_income_total")
        batch_op.drop_column("summary_transaction_count")
