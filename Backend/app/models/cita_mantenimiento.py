from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class CitaMantenimiento(TimestampMixin, Base):
    __tablename__ = "cita_mantenimiento"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE','CONFIRMADA','RECHAZADA','CANCELADA','COMPLETADA','NO_SHOW')",
            name="ck_cita_mantenimiento_estado",
        ),
    )

    id_cita: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
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
    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="RESTRICT"),
        nullable=False,
    )
    id_catalogo_servicio: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("catalogo_servicio_taller.id_catalogo_servicio", ondelete="SET NULL"),
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDIENTE'"),
    )
    motivo: Mapped[str | None] = mapped_column(String(255))
    notas_cliente: Mapped[str | None] = mapped_column(Text)
    notas_taller: Mapped[str | None] = mapped_column(Text)

    cliente: Mapped[Cliente] = relationship("Cliente", back_populates="citas_mantenimiento")
    vehiculo: Mapped[Vehiculo] = relationship("Vehiculo", back_populates="citas_mantenimiento")
    taller: Mapped[Taller] = relationship("Taller", back_populates="citas_mantenimiento")
    catalogo_servicio: Mapped[CatalogoServicioTaller | None] = relationship("CatalogoServicioTaller")
