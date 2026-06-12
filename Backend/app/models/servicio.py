from __future__ import annotations

from datetime import datetime
from decimal import Decimal

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, TimestampMixin


class Servicio(TimestampMixin, Base):
    __tablename__ = "servicio"
    __table_args__ = (
        CheckConstraint(
            """estado IN (
                'EN_ESPERA_ASIGNACION',
                'ASIGNADO',
                'EN_CAMINO',
                'EN_SITIO',
                'EN_DIAGNOSTICO_FISICO',
                'EN_REPARACION',
                'ESPERANDO_REPUESTOS',
                'COMPLETADO_PENDIENTE_CONFIRMACION',
                'FINALIZADO_PENDIENTE_PAGO',
                'PAGADO',
                'CANCELADO'
            )"""
        ),
        CheckConstraint("monto_precotizado_min IS NULL OR monto_precotizado_min >= 0"),
        CheckConstraint("monto_precotizado_max IS NULL OR monto_precotizado_max >= 0"),
        CheckConstraint("costo_mano_obra IS NULL OR costo_mano_obra >= 0"),
        CheckConstraint("costo_repuestos >= 0"),
        CheckConstraint("costo_total IS NULL OR costo_total >= 0"),
        CheckConstraint(
            """monto_precotizado_min IS NULL
            OR monto_precotizado_max IS NULL
            OR monto_precotizado_max >= monto_precotizado_min""",
            name="ck_servicio_rango_precotizacion",
        ),
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio",
            name="ck_servicio_fechas",
        ),
    )

    id_servicio: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_solicitud: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("solicitud_servicio.id_solicitud", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    id_seguro: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("seguro.id_seguro", ondelete="RESTRICT"),
    )
    id_persona_operario: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("operario.id_persona", ondelete="RESTRICT"),
    )
    estado: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        server_default=text("'EN_ESPERA_ASIGNACION'"),
    )
    codigo_precotizacion: Mapped[str | None] = mapped_column(String(50), unique=True)
    monto_precotizado_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    monto_precotizado_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    costo_mano_obra: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    costo_repuestos: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0"),
    )
    costo_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    comprobante: Mapped[str | None] = mapped_column(Text)
    confirmacion_cliente: Mapped[bool | None] = mapped_column(Boolean)
    fecha_confirmacion_cliente: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_asignacion_operario: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_llegada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones_cierre: Mapped[str | None] = mapped_column(Text)

    solicitud: Mapped[SolicitudServicio] = relationship(
        "SolicitudServicio",
        back_populates="servicio",
    )
    seguro: Mapped[Seguro | None] = relationship("Seguro", back_populates="servicios")
    operario: Mapped[Operario | None] = relationship(
        "Operario",
        back_populates="servicios_asignados",
    )
    evidencias: Mapped[list[Evidencia]] = relationship("Evidencia", back_populates="servicio")
    informe: Mapped[ServicioInforme | None] = relationship(
        "ServicioInforme",
        back_populates="servicio",
    )
    repuestos: Mapped[list[ServicioRepuesto]] = relationship(
        "ServicioRepuesto",
        back_populates="servicio",
    )
    ubicaciones: Mapped[list[ServicioUbicacion]] = relationship(
        "ServicioUbicacion",
        back_populates="servicio",
    )
    pago: Mapped[Pago | None] = relationship("Pago", back_populates="servicio")
    calificaciones: Mapped[list[Calificacion]] = relationship(
        "Calificacion",
        back_populates="servicio",
    )
    notificaciones: Mapped[list[Notificacion]] = relationship(
        "Notificacion",
        back_populates="servicio",
    )
    bitacoras: Mapped[list[Bitacora]] = relationship("Bitacora", back_populates="servicio")


class Evidencia(CreatedAtMixin, Base):
    __tablename__ = "evidencia"
    __table_args__ = (
        CheckConstraint("tipo_evidencia IN ('IMAGEN','AUDIO','VIDEO','DOCUMENTO','OTRO')"),
        CheckConstraint("categoria IN ('INCIDENTE','REPARACION','CIERRE')"),
        CheckConstraint("tamano_bytes IS NULL OR tamano_bytes >= 0"),
        CheckConstraint(
            "id_incidente IS NOT NULL OR id_servicio IS NOT NULL",
            name="ck_evidencia_relacion",
        ),
    )

    id_evidencia: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tipo_evidencia: Mapped[str] = mapped_column(String(20), nullable=False)
    categoria: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'INCIDENTE'"),
    )
    url_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    tamano_bytes: Mapped[int | None] = mapped_column(BigInteger)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    id_incidente: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("incidente.id_incidente", ondelete="CASCADE"),
    )
    id_servicio: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("servicio.id_servicio", ondelete="CASCADE"),
    )

    incidente: Mapped[Incidente | None] = relationship("Incidente", back_populates="evidencias")
    servicio: Mapped[Servicio | None] = relationship("Servicio", back_populates="evidencias")


class ServicioInforme(TimestampMixin, Base):
    __tablename__ = "servicio_informe"

    id_informe: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_servicio: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("servicio.id_servicio", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    accion_realizada: Mapped[str] = mapped_column(Text, nullable=False)
    diagnostico_fisico: Mapped[str | None] = mapped_column(Text)
    observaciones: Mapped[str | None] = mapped_column(Text)
    foto_cierre_url: Mapped[str | None] = mapped_column(Text)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    servicio: Mapped[Servicio] = relationship("Servicio", back_populates="informe")


class ServicioRepuesto(TimestampMixin, Base):
    __tablename__ = "servicio_repuesto"
    __table_args__ = (
        CheckConstraint("cantidad > 0"),
        CheckConstraint("costo_unitario >= 0"),
    )

    id_servicio_repuesto: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    id_servicio: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("servicio.id_servicio", ondelete="CASCADE"),
        nullable=False,
    )
    id_taller_repuesto: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("taller_repuesto.id_taller_repuesto", ondelete="SET NULL"),
    )
    descripcion: Mapped[str] = mapped_column(String(150), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("1"),
    )
    costo_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0"),
    )
    evidencia_url: Mapped[str | None] = mapped_column(Text)

    servicio: Mapped[Servicio] = relationship("Servicio", back_populates="repuestos")


class ServicioUbicacion(Base):
    __tablename__ = "servicio_ubicacion"

    id_ubicacion: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_servicio: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("servicio.id_servicio", ondelete="CASCADE"),
        nullable=False,
    )
    id_persona_operario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("operario.id_persona", ondelete="RESTRICT"),
        nullable=False,
    )
    latitud: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitud: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    precision_metros: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    velocidad_kmh: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    ruta_origen_latitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    ruta_origen_longitud: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))
    ruta_destino_latitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    ruta_destino_longitud: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))
    ruta_distancia_metros: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ruta_duracion_segundos: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ruta_geometria: Mapped[dict[str, object] | list[object] | str | None] = mapped_column(JSONB)

    servicio: Mapped[Servicio] = relationship("Servicio", back_populates="ubicaciones")
    operario: Mapped[Operario] = relationship("Operario", back_populates="ubicaciones_servicio")


class Calificacion(Base):
    __tablename__ = "calificacion"
    __table_args__ = (
        CheckConstraint("emisor_tipo IN ('CLIENTE','OPERARIO','ADMINISTRADOR')"),
        CheckConstraint("receptor_tipo IN ('PERSONA','TALLER')"),
        CheckConstraint("estrellas BETWEEN 1 AND 5"),
        CheckConstraint(
            """(receptor_tipo = 'PERSONA' AND id_receptor IS NOT NULL AND id_taller_calif IS NULL)
            OR
            (receptor_tipo = 'TALLER' AND id_receptor IS NULL AND id_taller_calif IS NOT NULL)""",
            name="ck_calificacion_destino",
        ),
    )

    id_calificacion: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    id_servicio: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("servicio.id_servicio", ondelete="CASCADE"),
        nullable=False,
    )
    id_emisor: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("persona.id_persona", ondelete="RESTRICT"),
        nullable=False,
    )
    id_receptor: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("persona.id_persona", ondelete="RESTRICT"),
    )
    id_taller_calif: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="RESTRICT"),
    )
    emisor_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    receptor_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    estrellas: Mapped[int] = mapped_column(Integer, nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    servicio: Mapped[Servicio] = relationship("Servicio", back_populates="calificaciones")
    emisor: Mapped[Persona] = relationship(
        "Persona",
        back_populates="calificaciones_emitidas",
        foreign_keys=[id_emisor],
    )
    receptor: Mapped[Persona | None] = relationship(
        "Persona",
        back_populates="calificaciones_recibidas",
        foreign_keys=[id_receptor],
    )
    taller_calif: Mapped[Taller | None] = relationship(
        "Taller",
        back_populates="calificaciones_recibidas",
        foreign_keys=[id_taller_calif],
    )


Index("ix_servicio_estado", Servicio.estado)
Index("ix_servicio_operario", Servicio.id_persona_operario)
Index("ix_evidencia_incidente", Evidencia.id_incidente)
Index("ix_evidencia_servicio", Evidencia.id_servicio)
Index("ix_servicio_repuesto_servicio", ServicioRepuesto.id_servicio)
Index(
    "ix_servicio_ubicacion_servicio_fecha",
    ServicioUbicacion.id_servicio,
    ServicioUbicacion.fecha_hora,
)
Index(
    "uq_calificacion_persona",
    Calificacion.id_servicio,
    Calificacion.id_emisor,
    Calificacion.id_receptor,
    unique=True,
    postgresql_where=Calificacion.id_receptor.is_not(None),
)
Index(
    "uq_calificacion_taller",
    Calificacion.id_servicio,
    Calificacion.id_emisor,
    Calificacion.id_taller_calif,
    unique=True,
    postgresql_where=Calificacion.id_taller_calif.is_not(None),
)

