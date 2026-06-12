"""add product catalog categories and stock fields

Revision ID: 91fa9228e9da
Revises: 8d9e0f1a2b3c
Create Date: 2026-06-12 14:45:59.105712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91fa9228e9da'
down_revision: Union[str, Sequence[str], None] = '8d9e0f1a2b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('categoria_producto',
        sa.Column('id_categoria', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('id_taller', sa.BigInteger(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('activo', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['id_taller'], ['taller.id_taller'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_categoria')
    )
    op.add_column('taller_repuesto', sa.Column('id_categoria', sa.BigInteger(), nullable=True))
    op.add_column('taller_repuesto', sa.Column('codigo', sa.String(length=50), nullable=True))
    op.add_column('taller_repuesto', sa.Column('unidad_medida', sa.String(length=30), server_default=sa.text("'UNIDAD'"), nullable=False))
    op.add_column('taller_repuesto', sa.Column('stock_actual', sa.Numeric(precision=10, scale=2), server_default=sa.text('0'), nullable=False))
    op.add_column('taller_repuesto', sa.Column('stock_minimo', sa.Numeric(precision=10, scale=2), nullable=True))
    op.create_foreign_key(None, 'taller_repuesto', 'categoria_producto', ['id_categoria'], ['id_categoria'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint(None, 'taller_repuesto', type_='foreignkey')
    op.drop_column('taller_repuesto', 'stock_minimo')
    op.drop_column('taller_repuesto', 'stock_actual')
    op.drop_column('taller_repuesto', 'unidad_medida')
    op.drop_column('taller_repuesto', 'codigo')
    op.drop_column('taller_repuesto', 'id_categoria')
    op.drop_table('categoria_producto')
