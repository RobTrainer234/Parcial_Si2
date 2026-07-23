from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Marca(TimestampMixin, Base):
    __tablename__ = "marca"

    id_marca: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    modelos: Mapped[list[Modelo]] = relationship("Modelo", back_populates="marca")


class Modelo(TimestampMixin, Base):
    __tablename__ = "modelo"
    __table_args__ = (
        UniqueConstraint("id_marca", "nombre", name="uq_modelo_por_marca"),
    )

    id_modelo: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_marca: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("marca.id_marca", ondelete="RESTRICT"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)

    marca: Mapped[Marca] = relationship("Marca", back_populates="modelos")
    vehiculos: Mapped[list[Vehiculo]] = relationship("Vehiculo", back_populates="modelo")


class Color(TimestampMixin, Base):
    __tablename__ = "color"

    id_color: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)

    vehiculos: Mapped[list[Vehiculo]] = relationship("Vehiculo", back_populates="color")


class Vehiculo(TimestampMixin, Base):
    __tablename__ = "vehiculo"
    __table_args__ = (
        CheckConstraint("anio BETWEEN 1900 AND 2100"),
    )

    id_vehiculo: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    placa: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    id_modelo: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("modelo.id_modelo", ondelete="RESTRICT"),
        nullable=False,
    )
    anio: Mapped[int] = mapped_column(nullable=False)
    id_color: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("color.id_color", ondelete="RESTRICT"),
        nullable=False,
    )
    id_persona: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cliente.id_persona", ondelete="RESTRICT"),
        nullable=False,
    )

    modelo: Mapped[Modelo] = relationship("Modelo", back_populates="vehiculos")
    color: Mapped[Color] = relationship("Color", back_populates="vehiculos")
    cliente: Mapped[Cliente] = relationship("Cliente", back_populates="vehiculos")
    incidentes: Mapped[list[Incidente]] = relationship("Incidente", back_populates="vehiculo")
    citas_mantenimiento: Mapped[list[CitaMantenimiento]] = relationship(
        "CitaMantenimiento",
        back_populates="vehiculo",
    )

