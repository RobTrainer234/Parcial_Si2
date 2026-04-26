from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DispositivoUsuario(Base):
    __tablename__ = "dispositivo_usuario"
    __table_args__ = (
        CheckConstraint("plataforma IN ('ANDROID','IOS','WEB')"),
    )

    id_dispositivo: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    plataforma: Mapped[str] = mapped_column(String(20), nullable=False)
    token_push: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    ultimo_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="dispositivos")


class Notificacion(Base):
    __tablename__ = "notificacion"
    __table_args__ = (
        CheckConstraint("canal IN ('PUSH','EMAIL','SMS','WEB')"),
        CheckConstraint("estado IN ('PENDIENTE','ENVIADA','FALLIDA','LEIDA')"),
        CheckConstraint(
            "payload IS NULL OR jsonb_typeof(payload) IN ('object','array')",
            name="ck_notificacion_payload_json",
        ),
    )

    id_notificacion: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    id_servicio: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("servicio.id_servicio", ondelete="CASCADE"),
    )
    id_solicitud: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("solicitud_servicio.id_solicitud", ondelete="CASCADE"),
    )
    canal: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PUSH'"),
    )
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Any | None] = mapped_column(JSONB)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDIENTE'"),
    )
    proveedor: Mapped[str | None] = mapped_column(String(50))
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    fecha_envio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_lectura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="notificaciones")
    servicio: Mapped[Servicio | None] = relationship("Servicio", back_populates="notificaciones")
    solicitud: Mapped[SolicitudServicio | None] = relationship(
        "SolicitudServicio",
        back_populates="notificaciones",
    )


Index("ix_notificacion_usuario_estado", Notificacion.id_usuario, Notificacion.estado)

