"""Add stable public references to orders."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_order_references"
down_revision: Union[str, None] = "20261111_phase4_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("order_reference", sa.String(length=32), nullable=True))
    bind = op.get_bind()
    orders = sa.table("orders", sa.column("id", sa.Uuid()), sa.column("order_reference", sa.String()))
    for (order_id,) in bind.execute(sa.select(orders.c.id)):
        bind.execute(orders.update().where(orders.c.id == order_id).values(
            order_reference=f"C2E-{order_id.hex[:16].upper()}"
        ))
    with op.batch_alter_table("orders") as batch:
        batch.alter_column("order_reference", existing_type=sa.String(length=32), nullable=False)
        batch.create_unique_constraint("uq_orders_order_reference", ["order_reference"])


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("uq_orders_order_reference", type_="unique")
        batch.drop_column("order_reference")
