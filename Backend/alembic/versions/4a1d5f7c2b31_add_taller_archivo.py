"""add taller archivo

Revision ID: 4a1d5f7c2b31
Revises: 00adee6a9cfb
Create Date: 2026-04-25 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a1d5f7c2b31"
down_revision: Union[str, Sequence[str], None] = "00adee6a9cfb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "taller_archivo",
        sa.Column("id_taller_archivo", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("id_taller", sa.BigInteger(), nullable=False),
        sa.Column("tipo_archivo", sa.String(length=30), nullable=False),
        sa.Column("nombre_archivo", sa.String(length=255), nullable=False),
        sa.Column("url_archivo", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("tamano_bytes", sa.BigInteger(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.CheckConstraint("tipo_archivo IN ('IMAGEN_TALLER','CERTIFICADO_TECNICO')"),
        sa.ForeignKeyConstraint(["id_taller"], ["taller.id_taller"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_taller_archivo"),
    )
    op.create_index("ix_taller_archivo_taller", "taller_archivo", ["id_taller"], unique=False)
    op.create_index(
        "ix_taller_archivo_taller_tipo_activo",
        "taller_archivo",
        ["id_taller", "tipo_archivo", "activo"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_taller_archivo_taller_tipo_activo", table_name="taller_archivo")
    op.drop_index("ix_taller_archivo_taller", table_name="taller_archivo")
    op.drop_table("taller_archivo")
