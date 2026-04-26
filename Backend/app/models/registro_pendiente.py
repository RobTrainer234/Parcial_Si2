from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin


class RegistroPendiente(CreatedAtMixin, Base):
    __tablename__ = "registro_pendiente"
    __table_args__ = (
        CheckConstraint("flujo IN ('CLIENTE','ADMINISTRADOR')"),
        CheckConstraint(
            "jsonb_typeof(payload_json) = 'object'",
            name="ck_registro_pendiente_payload_json_obj",
        ),
    )

    id_registro_pendiente: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    flujo: Mapped[str] = mapped_column(String(20), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    verification_code_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

