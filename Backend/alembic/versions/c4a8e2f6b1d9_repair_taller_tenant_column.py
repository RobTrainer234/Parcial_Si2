"""repair missing tenant assignment on legacy databases

Revision ID: c4a8e2f6b1d9
Revises: b5e7c9d1f3a4
Create Date: 2026-07-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c4a8e2f6b1d9"
down_revision: Union[str, Sequence[str], None] = "b5e7c9d1f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Older local dumps were stamped after multi-tenant migrations without these columns.
    op.execute(
        "CREATE TABLE IF NOT EXISTS tenant ("
        "id_tenant BIGSERIAL PRIMARY KEY, nombre VARCHAR(150) NOT NULL, "
        "codigo VARCHAR(50) NOT NULL UNIQUE, activo BOOLEAN NOT NULL DEFAULT TRUE, "
        "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
    )
    op.execute(
        "INSERT INTO tenant (nombre, codigo) "
        "SELECT 'Red principal', 'DEFAULT' "
        "WHERE NOT EXISTS (SELECT 1 FROM tenant)"
    )
    op.execute("ALTER TABLE taller ADD COLUMN IF NOT EXISTS id_tenant BIGINT")
    op.execute("UPDATE taller SET id_tenant = (SELECT MIN(id_tenant) FROM tenant) WHERE id_tenant IS NULL")
    op.execute("ALTER TABLE taller ALTER COLUMN id_tenant SET NOT NULL")
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_taller_tenant_repair') THEN "
        "ALTER TABLE taller ADD CONSTRAINT fk_taller_tenant_repair FOREIGN KEY (id_tenant) "
        "REFERENCES tenant(id_tenant) ON DELETE RESTRICT; "
        "END IF; END $$"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE taller DROP CONSTRAINT IF EXISTS fk_taller_tenant_repair")
    op.execute("ALTER TABLE taller DROP COLUMN IF EXISTS id_tenant")
