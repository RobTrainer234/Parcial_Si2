"""merge heads

Revision ID: 2a3b4c5d6e7f
Revises: 4a1d5f7c2b31, 1a2b3c4d5e6f
Create Date: 2026-06-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "2a3b4c5d6e7f"
down_revision: Union[str, Sequence[str], None] = (
    "4a1d5f7c2b31",
    "1a2b3c4d5e6f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
