from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class CategoriaProducto(TimestampMixin, Base):
    __tablename__ = "categoria_producto"

    id_categoria: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("taller.id_taller", ondelete="CASCADE"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )

    taller: Mapped[Taller] = relationship("Taller", back_populates="categorias_producto")
    productos: Mapped[list[TallerRepuesto]] = relationship(
        "TallerRepuesto", back_populates="categoria"
    )


class TallerRepuesto(TimestampMixin, Base):
    __tablename__ = "taller_repuesto"
    __table_args__ = (
        CheckConstraint("precio_unitario >= 0"),
        CheckConstraint("stock_actual >= 0"),
        CheckConstraint("stock_minimo IS NULL OR stock_minimo >= 0"),
        UniqueConstraint("id_taller", "nombre", name="uq_taller_repuesto_nombre"),
    )

    id_taller_repuesto: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("taller.id_taller", ondelete="CASCADE"), nullable=False
    )
    id_categoria: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categoria_producto.id_categoria", ondelete="SET NULL")
    )
    codigo: Mapped[str | None] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("0")
    )
    unidad_medida: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'UNIDAD'")
    )
    stock_actual: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    stock_minimo: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )

    taller: Mapped[Taller] = relationship("Taller", back_populates="productos")
    categoria: Mapped[CategoriaProducto | None] = relationship(
        "CategoriaProducto", back_populates="productos"
    )


# Import at the end to avoid circular imports
from .persona import Taller
