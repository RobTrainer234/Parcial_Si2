"""noop duplicate route fields migration for servicio_ubicacion

Revision ID: 5a6b7c8d9e0f
Revises: 39fc8d9d1223
Create Date: 2026-06-11 13:00:00.000000

"""
from typing import Sequence, Union

revision: str = "5a6b7c8d9e0f"
down_revision: Union[str, Sequence[str], None] = "39fc8d9d1223"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # These columns were already added by revision 3a4b5c6d7e8f.
    # Keep this revision in the chain as a no-op so clean upgrades do not
    # attempt to add the same columns twice.
    pass


def downgrade() -> None:
    pass
