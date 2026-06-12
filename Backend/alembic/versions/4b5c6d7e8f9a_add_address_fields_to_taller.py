"""add address fields to taller

Revision ID: 4b5c6d7e8f9a
Revises: 3a4b5c6d7e8f
Create Date: 2026-06-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b5c6d7e8f9a"
down_revision: Union[str, Sequence[str], None] = "3a4b5c6d7e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("taller", sa.Column("direccion", sa.String(255)))
    op.add_column("taller", sa.Column("ciudad", sa.String(100)))
    op.add_column("taller", sa.Column("zona", sa.String(100)))
    op.add_column("taller", sa.Column("referencia", sa.Text))


def downgrade() -> None:
    op.drop_column("taller", "referencia")
    op.drop_column("taller", "zona")
    op.drop_column("taller", "ciudad")
    op.drop_column("taller", "direccion")
