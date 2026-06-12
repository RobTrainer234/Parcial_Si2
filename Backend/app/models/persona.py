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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, TimestampMixin


class Persona(TimestampMixin, Base):
    __tablename__ = "persona"

    id_persona: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    ci: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    direccion: Mapped[str | None] = mapped_column(Text)

    usuario: Mapped[Usuario | None] = relationship("Usuario", back_populates="persona")
    cliente: Mapped[Cliente | None] = relationship("Cliente", back_populates="persona")
    administrador: Mapped[Administrador | None] = relationship(
        "Administrador",
        back_populates="persona",
    )
    operario: Mapped[Operario | None] = relationship("Operario", back_populates="persona")
    talleres_gerenciados: Mapped[list[GerenteTaller]] = relationship(
        "GerenteTaller",
        back_populates="persona",
        cascade="all, delete-orphan",
    )
    calificaciones_emitidas: Mapped[list[Calificacion]] = relationship(
        "Calificacion",
        back_populates="emisor",
        foreign_keys="Calificacion.id_emisor",
    )
    calificaciones_recibidas: Mapped[list[Calificacion]] = relationship(
        "Calificacion",
        back_populates="receptor",
        foreign_keys="Calificacion.id_receptor",
    )


class Taller(TimestampMixin, Base):
    __tablename__ = "taller"
    __table_args__ = (
        CheckConstraint("radio_accion_km > 0"),
        CheckConstraint(
            "reputacion_prom IS NULL OR (reputacion_prom >= 0 AND reputacion_prom <= 5)"
        ),
        CheckConstraint("total_expirados >= 0"),
        CheckConstraint("total_aceptados >= 0"),
    )

    id_taller: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre_comercial: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    latitud: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitud: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(255))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    zona: Mapped[str | None] = mapped_column(String(100))
    referencia: Mapped[str | None] = mapped_column(Text)
    radio_accion_km: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        server_default=text("10.00"),
    )
    reputacion_prom: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    acepta_seguro_propio: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    total_expirados: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    total_aceptados: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    administradores: Mapped[list[Administrador]] = relationship(
        "Administrador",
        back_populates="taller",
    )
    operarios: Mapped[list[Operario]] = relationship("Operario", back_populates="taller")
    especialidades: Mapped[list[TallerEspecialidad]] = relationship(
        "TallerEspecialidad",
        back_populates="taller",
    )
    seguros: Mapped[list[Seguro]] = relationship("Seguro", back_populates="taller")
    catalogos_servicio: Mapped[list[CatalogoServicioTaller]] = relationship(
        "CatalogoServicioTaller",
        back_populates="taller",
    )
    gerentes: Mapped[list[GerenteTaller]] = relationship(
        "GerenteTaller",
        back_populates="taller",
    )
    solicitudes_servicio: Mapped[list[SolicitudServicio]] = relationship(
        "SolicitudServicio",
        back_populates="taller",
    )
    archivos: Mapped[list[TallerArchivo]] = relationship(
        "TallerArchivo",
        back_populates="taller",
    )
    calificaciones_recibidas: Mapped[list[Calificacion]] = relationship(
        "Calificacion",
        back_populates="taller_calif",
        foreign_keys="Calificacion.id_taller_calif",
    )
    categorias_producto: Mapped[list[CategoriaProducto]] = relationship(
        "CategoriaProducto",
        back_populates="taller",
    )
    productos: Mapped[list[TallerRepuesto]] = relationship(
        "TallerRepuesto",
        back_populates="taller",
    )


class Usuario(TimestampMixin, Base):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(
            "tipo_usuario IN ('CLIENTE','OPERARIO','ADMINISTRADOR','ADMIN_SUCURSAL','ADMIN_GERENTE_SUCURSALES','SUPER_ADMIN')"
        ),
        CheckConstraint("intentos >= 0"),
        CheckConstraint(
            "reputacion_prom IS NULL OR (reputacion_prom >= 0 AND reputacion_prom <= 5)"
        ),
    )

    id_usuario: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_persona: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("persona.id_persona", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    email: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_usuario: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    intentos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    bloqueado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reputacion_prom: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    persona: Mapped[Persona] = relationship("Persona", back_populates="usuario")
    dispositivos: Mapped[list[DispositivoUsuario]] = relationship(
        "DispositivoUsuario",
        back_populates="usuario",
    )
    notificaciones: Mapped[list[Notificacion]] = relationship(
        "Notificacion",
        back_populates="usuario",
    )
    eventos_bitacora: Mapped[list[Bitacora]] = relationship(
        "Bitacora",
        back_populates="usuario",
    )
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        "PasswordResetToken",
        back_populates="usuario",
    )


class Cliente(TimestampMixin, Base):
    __tablename__ = "cliente"

    id_persona: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("persona.id_persona", ondelete="CASCADE"),
        primary_key=True,
    )

    persona: Mapped[Persona] = relationship("Persona", back_populates="cliente")
    vehiculos: Mapped[list[Vehiculo]] = relationship("Vehiculo", back_populates="cliente")
    seguros: Mapped[list[Seguro]] = relationship("Seguro", back_populates="cliente")
    incidentes: Mapped[list[Incidente]] = relationship("Incidente", back_populates="cliente")


class Administrador(TimestampMixin, Base):
    __tablename__ = "administrador"

    id_persona: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("persona.id_persona", ondelete="CASCADE"),
        primary_key=True,
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="RESTRICT"),
        nullable=False,
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )

    persona: Mapped[Persona] = relationship("Persona", back_populates="administrador")
    taller: Mapped[Taller] = relationship("Taller", back_populates="administradores")


class Operario(TimestampMixin, Base):
    __tablename__ = "operario"
    __table_args__ = (
        CheckConstraint(
            "estado_disponibilidad IN ('DISPONIBLE','EN_SERVICIO','NO_DISPONIBLE','BAJA')"
        ),
    )

    id_persona: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("persona.id_persona", ondelete="CASCADE"),
        primary_key=True,
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="RESTRICT"),
        nullable=False,
    )
    estado_disponibilidad: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'DISPONIBLE'"),
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    latitud_actual: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    longitud_actual: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))
    ultima_ubicacion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    persona: Mapped[Persona] = relationship("Persona", back_populates="operario")
    taller: Mapped[Taller] = relationship("Taller", back_populates="operarios")
    especialidades: Mapped[list[OperarioEspecialidad]] = relationship(
        "OperarioEspecialidad",
        back_populates="operario",
    )
    servicios_asignados: Mapped[list[Servicio]] = relationship(
        "Servicio",
        back_populates="operario",
    )
    ubicaciones_servicio: Mapped[list[ServicioUbicacion]] = relationship(
        "ServicioUbicacion",
        back_populates="operario",
    )


class Especialidad(TimestampMixin, Base):
    __tablename__ = "especialidad"
    __table_args__ = (
        CheckConstraint("nivel_complejidad BETWEEN 1 AND 5"),
    )

    id_especialidad: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel_complejidad: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    talleres: Mapped[list[TallerEspecialidad]] = relationship(
        "TallerEspecialidad",
        back_populates="especialidad",
    )
    operarios: Mapped[list[OperarioEspecialidad]] = relationship(
        "OperarioEspecialidad",
        back_populates="especialidad",
    )
    coberturas: Mapped[list[CoberturaEspecialidad]] = relationship(
        "CoberturaEspecialidad",
        back_populates="especialidad",
    )
    incidentes_reportados: Mapped[list[Incidente]] = relationship(
        "Incidente",
        back_populates="especialidad_reportada_cliente",
        foreign_keys="Incidente.id_especialidad_reportada_cliente",
    )
    incidentes_detectados: Mapped[list[Incidente]] = relationship(
        "Incidente",
        back_populates="especialidad_detectada",
        foreign_keys="Incidente.id_especialidad_detectada",
    )
    catalogos_servicio: Mapped[list[CatalogoServicioTaller]] = relationship(
        "CatalogoServicioTaller",
        back_populates="especialidad",
    )


class TallerEspecialidad(CreatedAtMixin, Base):
    __tablename__ = "taller_especialidad"

    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="CASCADE"),
        primary_key=True,
    )
    id_especialidad: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("especialidad.id_especialidad", ondelete="CASCADE"),
        primary_key=True,
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )

    taller: Mapped[Taller] = relationship("Taller", back_populates="especialidades")
    especialidad: Mapped[Especialidad] = relationship(
        "Especialidad",
        back_populates="talleres",
    )


class OperarioEspecialidad(CreatedAtMixin, Base):
    __tablename__ = "operario_especialidad"
    __table_args__ = (
        CheckConstraint("anios_experiencia >= 0"),
    )

    id_persona: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("operario.id_persona", ondelete="CASCADE"),
        primary_key=True,
    )
    id_especialidad: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("especialidad.id_especialidad", ondelete="CASCADE"),
        primary_key=True,
    )
    anios_experiencia: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    certificacion_url: Mapped[str | None] = mapped_column(Text)

    operario: Mapped[Operario] = relationship("Operario", back_populates="especialidades")
    especialidad: Mapped[Especialidad] = relationship(
        "Especialidad",
        back_populates="operarios",
    )


class GerenteTaller(CreatedAtMixin, Base):
    __tablename__ = "gerente_taller"

    id_persona: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("persona.id_persona", ondelete="CASCADE"),
        primary_key=True,
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="CASCADE"),
        primary_key=True,
    )

    persona: Mapped[Persona] = relationship("Persona", back_populates="talleres_gerenciados")
    taller: Mapped[Taller] = relationship("Taller", back_populates="gerentes")


Index("uq_usuario_email_lower", func.lower(Usuario.email), unique=True)
