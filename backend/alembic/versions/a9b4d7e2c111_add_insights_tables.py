"""add insights tables

Revision ID: a9b4d7e2c111
Revises: f4b19be77f6d
Create Date: 2026-05-10 18:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a9b4d7e2c111"
down_revision = "5aa8b3db4f5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insight_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "running", "completed", "failed", name="insightrunstatus"
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("result_json", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_insight_runs_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insight_runs")),
    )
    op.create_index(
        op.f("ix_insight_runs_user_id"), "insight_runs", ["user_id"], unique=False
    )

    op.create_table(
        "anomaly_decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("transaction_id", sa.String(), nullable=False),
        sa.Column("is_anomaly", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name=op.f("fk_anomaly_decisions_transaction_id_transactions"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_anomaly_decisions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_anomaly_decisions")),
    )
    op.create_index(
        op.f("ix_anomaly_decisions_user_id"),
        "anomaly_decisions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_anomaly_decisions_transaction_id"),
        "anomaly_decisions",
        ["transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_anomaly_decisions_transaction_id"), table_name="anomaly_decisions"
    )
    op.drop_index(op.f("ix_anomaly_decisions_user_id"), table_name="anomaly_decisions")
    op.drop_table("anomaly_decisions")
    op.drop_index(op.f("ix_insight_runs_user_id"), table_name="insight_runs")
    op.drop_table("insight_runs")
    op.execute("DROP TYPE IF EXISTS insightrunstatus")
