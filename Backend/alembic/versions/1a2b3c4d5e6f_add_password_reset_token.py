"""add password_reset_token

Revision ID: 1a2b3c4d5e6f
Revises: 00adee6a9cfb
Create Date: 2026-06-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = '00adee6a9cfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('password_reset_token',
        sa.Column('id_reset_token', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('id_usuario', sa.BigInteger(), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuario.id_usuario'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_reset_token'),
    )
    op.create_index(
        'ix_password_reset_token_token_hash', 'password_reset_token', ['token_hash'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_password_reset_token_token_hash', table_name='password_reset_token')
    op.drop_table('password_reset_token')
