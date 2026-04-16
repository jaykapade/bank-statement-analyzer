"""change transaction amount to numeric

Revision ID: 4f9a2db66a11
Revises: 61b89badc63c
Create Date: 2026-04-15 23:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f9a2db66a11"
down_revision: Union[str, Sequence[str], None] = "61b89badc63c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.alter_column(
            "amount",
            existing_type=sa.Float(),
            type_=sa.Numeric(18, 2),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.alter_column(
            "amount",
            existing_type=sa.Numeric(18, 2),
            type_=sa.Float(),
            existing_nullable=True,
        )

