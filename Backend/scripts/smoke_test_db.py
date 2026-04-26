from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import func, select, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models import Especialidad, MetodoPago


def main() -> None:
    with SessionLocal() as db:
        select_1 = db.execute(text("SELECT 1")).scalar_one()
        especialidad_count = db.scalar(select(func.count()).select_from(Especialidad)) or 0
        metodo_pago_count = db.scalar(select(func.count()).select_from(MetodoPago)) or 0
        especialidades_sample = list(
            db.scalars(select(Especialidad.nombre).order_by(Especialidad.nombre).limit(5))
        )
        metodos_pago_sample = list(
            db.scalars(select(MetodoPago.nombre).order_by(MetodoPago.nombre).limit(5))
        )

    print(f"SELECT 1: {select_1}")
    print(f"especialidad_count: {especialidad_count}")
    print(f"metodo_pago_count: {metodo_pago_count}")
    print(f"especialidades_sample: {especialidades_sample}")
    print(f"metodos_pago_sample: {metodos_pago_sample}")


if __name__ == "__main__":
    main()
