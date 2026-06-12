"""add admin_sucursal role and gerente_taller table

Revision ID: 39fc8d9d1223
Revises: 622e32c9bbe3
Create Date: 2026-06-11 12:10:37.495020

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "39fc8d9d1223"
down_revision: Union[str, Sequence[str], None] = "622e32c9bbe3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_CHECK = "'ADMINISTRADOR','CLIENTE','OPERARIO'"
NEW_CHECK = "'ADMINISTRADOR','ADMIN_SUCURSAL','ADMIN_GERENTE_SUCURSALES','CLIENTE','OPERARIO'"


def upgrade() -> None:
    # Create gerente_taller junction table
    op.create_table(
        "gerente_taller",
        sa.Column("id_persona", sa.BigInteger(), nullable=False),
        sa.Column("id_taller", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["id_persona"], ["persona.id_persona"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["id_taller"], ["taller.id_taller"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id_persona", "id_taller"),
    )

    # Extend CHECK constraint on usuario.tipo_usuario to include new roles
    op.execute(
        f"ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_tipo_usuario_check;"
    )
    op.execute(
        f"ALTER TABLE usuario ADD CONSTRAINT usuario_tipo_usuario_check "
        f"CHECK (tipo_usuario IN ({NEW_CHECK}));"
    )


def downgrade() -> None:
    # Restore original CHECK constraint
    op.execute(
        f"ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_tipo_usuario_check;"
    )
    op.execute(
        f"ALTER TABLE usuario ADD CONSTRAINT usuario_tipo_usuario_check "
        f"CHECK (tipo_usuario IN ({OLD_CHECK}));"
    )

    # Drop gerente_taller table
    op.drop_table("gerente_taller")
