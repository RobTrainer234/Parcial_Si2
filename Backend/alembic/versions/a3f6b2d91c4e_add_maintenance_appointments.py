"""add maintenance appointments

Revision ID: a3f6b2d91c4e
Revises: 91fa9228e9da
Create Date: 2026-07-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3f6b2d91c4e"
down_revision: Union[str, Sequence[str], None] = "91fa9228e9da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cita_mantenimiento",
        sa.Column("id_cita", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("id_cliente", sa.BigInteger(), nullable=False),
        sa.Column("id_vehiculo", sa.BigInteger(), nullable=False),
        sa.Column("id_taller", sa.BigInteger(), nullable=False),
        sa.Column("id_catalogo_servicio", sa.BigInteger(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=20), server_default=sa.text("'PENDIENTE'"), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column("notas_cliente", sa.Text(), nullable=True),
        sa.Column("notas_taller", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("estado IN ('PENDIENTE','CONFIRMADA','RECHAZADA','CANCELADA','COMPLETADA','NO_SHOW')", name="ck_cita_mantenimiento_estado"),
        sa.ForeignKeyConstraint(["id_catalogo_servicio"], ["catalogo_servicio_taller.id_catalogo_servicio"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id_cliente"], ["cliente.id_persona"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["id_taller"], ["taller.id_taller"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["id_vehiculo"], ["vehiculo.id_vehiculo"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id_cita"),
    )
    op.create_index("ix_cita_mantenimiento_cliente_fecha", "cita_mantenimiento", ["id_cliente", "fecha_hora"])
    op.create_index("ix_cita_mantenimiento_taller_fecha", "cita_mantenimiento", ["id_taller", "fecha_hora"])


def downgrade() -> None:
    op.drop_index("ix_cita_mantenimiento_taller_fecha", table_name="cita_mantenimiento")
    op.drop_index("ix_cita_mantenimiento_cliente_fecha", table_name="cita_mantenimiento")
    op.drop_table("cita_mantenimiento")
