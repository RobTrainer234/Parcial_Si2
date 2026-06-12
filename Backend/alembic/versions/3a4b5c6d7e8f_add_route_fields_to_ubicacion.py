"""add route fields to servicio_ubicacion

Revision ID: 3a4b5c6d7e8f
Revises: 2a3b4c5d6e7f
Create Date: 2026-06-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "3a4b5c6d7e8f"
down_revision: Union[str, Sequence[str], None] = "2a3b4c5d6e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("servicio_ubicacion", sa.Column("ruta_origen_latitud", sa.Numeric(10, 8)))
    op.add_column("servicio_ubicacion", sa.Column("ruta_origen_longitud", sa.Numeric(11, 8)))
    op.add_column("servicio_ubicacion", sa.Column("ruta_destino_latitud", sa.Numeric(10, 8)))
    op.add_column("servicio_ubicacion", sa.Column("ruta_destino_longitud", sa.Numeric(11, 8)))
    op.add_column("servicio_ubicacion", sa.Column("ruta_distancia_metros", sa.Numeric(12, 2)))
    op.add_column("servicio_ubicacion", sa.Column("ruta_duracion_segundos", sa.Numeric(12, 2)))
    op.add_column("servicio_ubicacion", sa.Column("ruta_geometria", JSONB))


def downgrade() -> None:
    op.drop_column("servicio_ubicacion", "ruta_geometria")
    op.drop_column("servicio_ubicacion", "ruta_duracion_segundos")
    op.drop_column("servicio_ubicacion", "ruta_distancia_metros")
    op.drop_column("servicio_ubicacion", "ruta_destino_longitud")
    op.drop_column("servicio_ubicacion", "ruta_destino_latitud")
    op.drop_column("servicio_ubicacion", "ruta_origen_longitud")
    op.drop_column("servicio_ubicacion", "ruta_origen_latitud")
