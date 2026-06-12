"""add local_uuid deduplication to incidente

Revision ID: 6b7c8d9e0f1a
Revises: 5a6b7c8d9e0f
Create Date: 2026-06-12 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6b7c8d9e0f1a"
down_revision: Union[str, Sequence[str], None] = "5a6b7c8d9e0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("incidente", sa.Column("local_uuid", sa.String(length=64), nullable=True))
    op.create_index(
        "ux_incidente_cliente_local_uuid",
        "incidente",
        ["id_cliente", "local_uuid"],
        unique=True,
        postgresql_where=sa.text("local_uuid IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_incidente_cliente_local_uuid", table_name="incidente")
    op.drop_column("incidente", "local_uuid")
