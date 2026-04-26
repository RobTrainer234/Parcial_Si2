from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, TimestampMixin


class TipoCobertura(TimestampMixin, Base):
    __tablename__ = "tipo_cobertura"

    id_cobertura: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    descripcion_plan: Mapped[str | None] = mapped_column(Text)

    especialidades: Mapped[list[CoberturaEspecialidad]] = relationship(
        "CoberturaEspecialidad",
        back_populates="cobertura",
    )
    seguros: Mapped[list[Seguro]] = relationship("Seguro", back_populates="cobertura")


class CoberturaEspecialidad(CreatedAtMixin, Base):
    __tablename__ = "cobertura_especialidad"

    id_cobertura: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tipo_cobertura.id_cobertura", ondelete="CASCADE"),
        primary_key=True,
    )
    id_especialidad: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("especialidad.id_especialidad", ondelete="CASCADE"),
        primary_key=True,
    )

    cobertura: Mapped[TipoCobertura] = relationship(
        "TipoCobertura",
        back_populates="especialidades",
    )
    especialidad: Mapped[Especialidad] = relationship(
        "Especialidad",
        back_populates="coberturas",
    )


class Seguro(TimestampMixin, Base):
    __tablename__ = "seguro"
    __table_args__ = (
        CheckConstraint(
            "monto_maximo IS NULL OR monto_maximo >= 0",
        ),
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="ck_seguro_fechas",
        ),
    )

    id_seguro: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_cliente: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cliente.id_persona", ondelete="RESTRICT"),
        nullable=False,
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="RESTRICT"),
        nullable=False,
    )
    id_cobertura: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tipo_cobertura.id_cobertura", ondelete="RESTRICT"),
        nullable=False,
    )
    numero_poliza: Mapped[str | None] = mapped_column(String(50))
    monto_maximo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )

    cliente: Mapped[Cliente] = relationship("Cliente", back_populates="seguros")
    taller: Mapped[Taller] = relationship("Taller", back_populates="seguros")
    cobertura: Mapped[TipoCobertura] = relationship("TipoCobertura", back_populates="seguros")
    servicios: Mapped[list[Servicio]] = relationship("Servicio", back_populates="seguro")
