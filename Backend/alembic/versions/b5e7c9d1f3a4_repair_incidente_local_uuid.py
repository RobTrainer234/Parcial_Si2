"""repair missing incidente local uuid on legacy databases

Revision ID: b5e7c9d1f3a4
Revises: a3f6b2d91c4e
Create Date: 2026-07-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b5e7c9d1f3a4"
down_revision: Union[str, Sequence[str], None] = "a3f6b2d91c4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Some local databases were stamped past the original migration without the column.
    op.execute("ALTER TABLE incidente ADD COLUMN IF NOT EXISTS local_uuid VARCHAR(64)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_incidente_cliente_local_uuid "
        "ON incidente (id_cliente, local_uuid) WHERE local_uuid IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_incidente_cliente_local_uuid")
    op.execute("ALTER TABLE incidente DROP COLUMN IF EXISTS local_uuid")
