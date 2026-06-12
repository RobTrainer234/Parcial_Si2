"""create tenant and assign workshops

Revision ID: 7c8d9e0f1a2b
Revises: 6b7c8d9e0f1a
Create Date: 2026-06-12 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c8d9e0f1a2b"
down_revision: Union[str, Sequence[str], None] = "6b7c8d9e0f1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


tenant_table = sa.table(
    "tenant",
    sa.column("id_tenant", sa.BigInteger()),
    sa.column("nombre", sa.String(length=150)),
    sa.column("codigo", sa.String(length=50)),
    sa.column("activo", sa.Boolean()),
)


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id_tenant", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("codigo", name="uq_tenant_codigo"),
    )

    op.add_column("taller", sa.Column("id_tenant", sa.BigInteger(), nullable=True))

    bind = op.get_bind()
    result = bind.execute(
        sa.insert(tenant_table).values(
            nombre="Tenant Principal",
            codigo="DEFAULT",
            activo=True,
        )
    )
    inserted_primary_key = result.inserted_primary_key
    default_tenant_id = inserted_primary_key[0] if inserted_primary_key else None
    if default_tenant_id is None:
        default_tenant_id = bind.execute(
            sa.select(tenant_table.c.id_tenant).where(tenant_table.c.codigo == "DEFAULT")
        ).scalar_one()

    bind.execute(
        sa.text(
            """
            UPDATE taller
            SET id_tenant = :tenant_id
            WHERE id_tenant IS NULL
            """
        ),
        {"tenant_id": default_tenant_id},
    )

    op.create_foreign_key(
        "fk_taller_tenant",
        "taller",
        "tenant",
        ["id_tenant"],
        ["id_tenant"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_taller_tenant", "taller", ["id_tenant"], unique=False)
    op.alter_column("taller", "id_tenant", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_taller_tenant", table_name="taller")
    op.drop_constraint("fk_taller_tenant", "taller", type_="foreignkey")
    op.drop_column("taller", "id_tenant")
    op.drop_table("tenant")
