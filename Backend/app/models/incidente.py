from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Incidente(TimestampMixin, Base):
    __tablename__ = "incidente"
    __table_args__ = (
        CheckConstraint(
            """estado IN (
                'REPORTADO',
                'EN_TRIAJE',
                'DIAGNOSTICADO',
                'EN_MATCHMAKING',
                'EN_PROCESO',
                'FINALIZADO',
                'CANCELADO'
            )"""
        ),
        CheckConstraint(
            "severidad IS NULL OR severidad IN ('BAJA','MEDIA','ALTA','CRITICA')"
        ),
        CheckConstraint(
            "confianza_ia IS NULL OR (confianza_ia >= 0 AND confianza_ia <= 100)"
        ),
        CheckConstraint(
            "diagnostico_ia_json IS NULL OR jsonb_typeof(diagnostico_ia_json) = 'object'",
            name="ck_diagnostico_ia_json_obj",
        ),
        CheckConstraint(
            "etiquetas_imagen IS NULL OR jsonb_typeof(etiquetas_imagen) IN ('array','object')",
            name="ck_etiquetas_imagen_json_arr",
        ),
    )

    id_incidente: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    latitud: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitud: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    descripcion_cliente: Mapped[str] = mapped_column(Text, nullable=False)
    local_uuid: Mapped[str | None] = mapped_column(String(64))
    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'REPORTADO'"),
    )
    severidad: Mapped[str | None] = mapped_column(String(20))
    id_cliente: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cliente.id_persona", ondelete="RESTRICT"),
        nullable=False,
    )
    id_vehiculo: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehiculo.id_vehiculo", ondelete="RESTRICT"),
        nullable=False,
    )
    id_especialidad_reportada_cliente: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("especialidad.id_especialidad", ondelete="RESTRICT"),
        nullable=False,
    )
    id_especialidad_detectada: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("especialidad.id_especialidad", ondelete="RESTRICT"),
    )
    diagnostico_ia_resumen: Mapped[str | None] = mapped_column(Text)
    diagnostico_ia_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confianza_ia: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    transcripcion_audio: Mapped[str | None] = mapped_column(Text)
    etiquetas_imagen: Mapped[Any | None] = mapped_column(JSONB)
    fecha_triaje: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requiere_revision_manual: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )

    cliente: Mapped[Cliente] = relationship("Cliente", back_populates="incidentes")
    vehiculo: Mapped[Vehiculo] = relationship("Vehiculo", back_populates="incidentes")
    especialidad_reportada_cliente: Mapped[Especialidad] = relationship(
        "Especialidad",
        back_populates="incidentes_reportados",
        foreign_keys=[id_especialidad_reportada_cliente],
    )
    especialidad_detectada: Mapped[Especialidad | None] = relationship(
        "Especialidad",
        back_populates="incidentes_detectados",
        foreign_keys=[id_especialidad_detectada],
    )
    solicitudes: Mapped[list[SolicitudServicio]] = relationship(
        "SolicitudServicio",
        back_populates="incidente",
    )
    evidencias: Mapped[list[Evidencia]] = relationship("Evidencia", back_populates="incidente")
    bitacoras: Mapped[list[Bitacora]] = relationship("Bitacora", back_populates="incidente")


class CatalogoServicioTaller(TimestampMixin, Base):
    __tablename__ = "catalogo_servicio_taller"
    __table_args__ = (
        CheckConstraint("precio_base_min >= 0"),
        CheckConstraint("precio_base_max >= 0"),
        CheckConstraint(
            "precio_base_max >= precio_base_min",
            name="ck_catalogo_rango_precio",
        ),
        UniqueConstraint("id_taller", "nombre", name="uq_catalogo_taller_nombre"),
    )

    id_catalogo_servicio: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="CASCADE"),
        nullable=False,
    )
    id_especialidad: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("especialidad.id_especialidad", ondelete="RESTRICT"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio_base_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    precio_base_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    incluye_repuestos_basicos: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )

    taller: Mapped[Taller] = relationship("Taller", back_populates="catalogos_servicio")
    especialidad: Mapped[Especialidad] = relationship(
        "Especialidad",
        back_populates="catalogos_servicio",
    )


class SolicitudServicio(TimestampMixin, Base):
    __tablename__ = "solicitud_servicio"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE','ACEPTADA','RECHAZADA','EXPIRADA','CANCELADA','DESCARTADA')"
        ),
        CheckConstraint(
            "score_proximidad IS NULL OR (score_proximidad >= 0 AND score_proximidad <= 1)"
        ),
        CheckConstraint(
            "score_reputacion IS NULL OR (score_reputacion >= 0 AND score_reputacion <= 1)"
        ),
        CheckConstraint("score_total IS NULL OR (score_total >= 0 AND score_total <= 1)"),
        CheckConstraint("ranking_posicion IS NULL OR ranking_posicion > 0"),
        CheckConstraint("intento_numero > 0"),
        CheckConstraint("fecha_expiracion >= fecha_envio", name="ck_solicitud_fechas"),
        UniqueConstraint(
            "id_incidente",
            "id_taller",
            "intento_numero",
            name="uq_solicitud_incidente_taller_intento",
        ),
    )

    id_solicitud: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    id_incidente: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("incidente.id_incidente", ondelete="CASCADE"),
        nullable=False,
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_respuesta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDIENTE'"),
    )
    motivo_cierre: Mapped[str | None] = mapped_column(String(200))
    prioridad_seguro: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    score_proximidad: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    score_reputacion: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    score_total: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    ranking_posicion: Mapped[int | None] = mapped_column(Integer)
    intento_numero: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    es_actual: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )

    incidente: Mapped[Incidente] = relationship("Incidente", back_populates="solicitudes")
    taller: Mapped[Taller] = relationship("Taller", back_populates="solicitudes_servicio")
    servicio: Mapped[Servicio | None] = relationship("Servicio", back_populates="solicitud")
    notificaciones: Mapped[list[Notificacion]] = relationship(
        "Notificacion",
        back_populates="solicitud",
    )
    bitacoras: Mapped[list[Bitacora]] = relationship("Bitacora", back_populates="solicitud")


Index("ix_incidente_cliente", Incidente.id_cliente)
Index("ix_incidente_estado", Incidente.estado)
Index("ix_incidente_especialidad_detectada", Incidente.id_especialidad_detectada)
Index(
    "ux_incidente_cliente_local_uuid",
    Incidente.id_cliente,
    Incidente.local_uuid,
    unique=True,
    postgresql_where=Incidente.local_uuid.is_not(None),
)
Index("ix_solicitud_taller_estado", SolicitudServicio.id_taller, SolicitudServicio.estado)
Index(
    "ix_solicitud_incidente_estado",
    SolicitudServicio.id_incidente,
    SolicitudServicio.estado,
)
Index(
    "ux_solicitud_incidente_actual",
    SolicitudServicio.id_incidente,
    unique=True,
    postgresql_where=text("es_actual = TRUE AND estado IN ('PENDIENTE','ACEPTADA')"),
)
Index(
    "ux_solicitud_incidente_aceptada",
    SolicitudServicio.id_incidente,
    unique=True,
    postgresql_where=text("estado = 'ACEPTADA'"),
)
