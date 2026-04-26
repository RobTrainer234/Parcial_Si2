from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, CHAR, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class MetodoPago(TimestampMixin, Base):
    __tablename__ = "metodo_pago"

    id_metodo: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )

    pagos: Mapped[list[Pago]] = relationship("Pago", back_populates="metodo")


class Pago(TimestampMixin, Base):
    __tablename__ = "pago"
    __table_args__ = (
        CheckConstraint("monto >= 0"),
        CheckConstraint("estado IN ('PENDIENTE','CONFIRMADO','RECHAZADO','ANULADO')"),
        CheckConstraint(
            "payload_pasarela IS NULL OR jsonb_typeof(payload_pasarela) = 'object'",
            name="ck_pago_payload_json_obj",
        ),
    )

    id_pago: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_servicio: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("servicio.id_servicio", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    id_metodo: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("metodo_pago.id_metodo", ondelete="RESTRICT"),
        nullable=False,
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(
        CHAR(3),
        nullable=False,
        server_default=text("'BOB'"),
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDIENTE'"),
    )
    referencia_externa: Mapped[str | None] = mapped_column(String(100))
    token_pago: Mapped[str | None] = mapped_column(String(150))
    qr_url: Mapped[str | None] = mapped_column(Text)
    payload_pasarela: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    comprobante: Mapped[str | None] = mapped_column(Text)
    fecha_solicitud: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    fecha_confirmacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    servicio: Mapped[Servicio] = relationship("Servicio", back_populates="pago")
    metodo: Mapped[MetodoPago] = relationship("MetodoPago", back_populates="pagos")
    bitacoras: Mapped[list[Bitacora]] = relationship("Bitacora", back_populates="pago")


Index("ix_pago_estado", Pago.estado)
