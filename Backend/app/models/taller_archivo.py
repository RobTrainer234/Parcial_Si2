from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TallerArchivo(Base):
    __tablename__ = "taller_archivo"
    __table_args__ = (
        CheckConstraint("tipo_archivo IN ('IMAGEN_TALLER','CERTIFICADO_TECNICO')"),
    )

    id_taller_archivo: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    id_taller: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("taller.id_taller", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_archivo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    url_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    tamano_bytes: Mapped[int | None] = mapped_column(BigInteger)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    descripcion: Mapped[str | None] = mapped_column(Text)

    taller: Mapped[Taller] = relationship("Taller", back_populates="archivos")
