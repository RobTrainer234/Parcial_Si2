"""add route fields to servicio_ubicacion

Revision ID: 5a6b7c8d9e0f
Revises: 39fc8d9d1223
Create Date: 2026-06-11 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "5a6b7c8d9e0f"
down_revision: Union[str, Sequence[str], None] = "39fc8d9d1223"
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
