from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Especialidad, MetodoPago


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "status": "ok",
    }


@router.get("/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        select_1 = db.execute(text("SELECT 1")).scalar_one()
        especialidad_count = db.scalar(select(func.count()).select_from(Especialidad)) or 0
        metodo_pago_count = db.scalar(select(func.count()).select_from(MetodoPago)) or 0
        especialidades_sample = list(
            db.scalars(
                select(Especialidad.nombre).order_by(Especialidad.nombre).limit(5)
            )
        )
        metodos_pago_sample = list(
            db.scalars(select(MetodoPago.nombre).order_by(MetodoPago.nombre).limit(5))
        )
        alembic_revision = db.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        ).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "database": "sis_auxilio",
                "message": "Database smoke test failed.",
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    return {
        "status": "ok",
        "database": "sis_auxilio",
        "select_1": select_1,
        "especialidad_count": especialidad_count,
        "metodo_pago_count": metodo_pago_count,
        "especialidades_sample": especialidades_sample,
        "metodos_pago_sample": metodos_pago_sample,
        "alembic_revision": alembic_revision,
    }
