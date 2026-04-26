from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Bitacora(Base):
    __tablename__ = "bitacora"
    __table_args__ = (
        CheckConstraint(
            """entidad_principal IN (
                'INCIDENTE',
                'SOLICITUD',
                'SERVICIO',
                'PAGO',
                'IA',
                'NOTIFICACION',
                'USUARIO',
                'SISTEMA'
            )"""
        ),
        CheckConstraint(
            "datos_originales IS NULL OR jsonb_typeof(datos_originales) IN ('object','array','string','number','boolean','null')",
            name="ck_bitacora_datos_originales_json",
        ),
        CheckConstraint(
            "datos_nuevos IS NULL OR jsonb_typeof(datos_nuevos) IN ('object','array','string','number','boolean','null')",
            name="ck_bitacora_datos_nuevos_json",
        ),
    )

    id_bitacora: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    entidad_principal: Mapped[str] = mapped_column(String(30), nullable=False)
    id_entidad_principal: Mapped[int | None] = mapped_column(BigInteger)
    datos_originales: Mapped[Any | None] = mapped_column(JSONB)
    datos_nuevos: Mapped[Any | None] = mapped_column(JSONB)
    ip_origen: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    # El hash y la politica append-only quedan controlados por triggers en PostgreSQL.
    hash_evento: Mapped[str] = mapped_column(String(32), nullable=False)
    id_usuario: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id_usuario", ondelete="SET NULL"),
    )
    id_incidente: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("incidente.id_incidente", ondelete="SET NULL"),
    )
    id_solicitud: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("solicitud_servicio.id_solicitud", ondelete="SET NULL"),
    )
    id_servicio: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("servicio.id_servicio", ondelete="SET NULL"),
    )
    id_pago: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("pago.id_pago", ondelete="SET NULL"),
    )
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    usuario: Mapped[Usuario | None] = relationship("Usuario", back_populates="eventos_bitacora")
    incidente: Mapped[Incidente | None] = relationship("Incidente", back_populates="bitacoras")
    solicitud: Mapped[SolicitudServicio | None] = relationship(
        "SolicitudServicio",
        back_populates="bitacoras",
    )
    servicio: Mapped[Servicio | None] = relationship("Servicio", back_populates="bitacoras")
    pago: Mapped[Pago | None] = relationship("Pago", back_populates="bitacoras")


Index("ix_bitacora_fecha", Bitacora.fecha_hora)
Index("ix_bitacora_servicio", Bitacora.id_servicio)
Index("ix_bitacora_incidente", Bitacora.id_incidente)
Index("ix_bitacora_solicitud", Bitacora.id_solicitud)
Index("ix_bitacora_pago", Bitacora.id_pago)
Index("ix_bitacora_entidad", Bitacora.entidad_principal, Bitacora.id_entidad_principal)

