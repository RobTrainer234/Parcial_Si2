from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import create_app
from app.models import Servicio


def _assert_model_fields() -> None:
    required_fields = (
        "codigo_precotizacion",
        "monto_precotizado_min",
        "monto_precotizado_max",
    )
    missing = [field for field in required_fields if not hasattr(Servicio, field)]
    if missing:
        raise SystemExit(f"Servicio is missing required CU20 fields: {missing}")


def _assert_route_mounted() -> None:
    app = create_app()
    routes = {route.path for route in app.routes}
    expected_route = "/client/services/{service_id}/prequotation"
    if expected_route not in routes:
        raise SystemExit(f"CU20 route is not mounted: {expected_route}")


def _assert_migration_columns() -> None:
    migration_path = (
        BACKEND_DIR / "alembic" / "versions" / "8af1d09b1b3b_initial_schema.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")
    required_tokens = (
        "codigo_precotizacion",
        "monto_precotizado_min",
        "monto_precotizado_max",
    )
    missing = [token for token in required_tokens if token not in migration_text]
    if missing:
        raise SystemExit(f"Alembic migration is missing CU20 columns: {missing}")


def main() -> None:
    _assert_model_fields()
    _assert_route_mounted()
    _assert_migration_columns()

    print("CU20 structural checks: OK")
    print()
    print("Manual API verification checklist:")
    print("1. Aceptacion exitosa con precotizacion")
    print("   - Precondiciones: incidente triageado, catalogo activo compatible, solicitud PENDIENTE.")
    print("   - Endpoint: POST /workshop/requests/{request_id}/decision {\"decision\":\"ACEPTAR\"}")
    print("   - Esperado: 200, service_id creado, prequotation_code/min/max no nulos.")
    print()
    print("2. Rechazo 409 sin catalogo activo compatible")
    print("   - Precondiciones: solicitud PENDIENTE, triage completo, taller sin CatalogoServicioTaller activo para la especialidad detectada.")
    print("   - Endpoint: POST /workshop/requests/{request_id}/decision {\"decision\":\"ACEPTAR\"}")
    print("   - Esperado: 409 con mensaje sobre CU26 catalog before accepting.")
    print()
    print("3. Rechazo 409 por triaje incompleto")
    print("   - Precondiciones: solicitud PENDIENTE con incidente sin fecha_triaje o sin id_especialidad_detectada o con requiere_revision_manual=true.")
    print("   - Endpoint: POST /workshop/requests/{request_id}/decision {\"decision\":\"ACEPTAR\"}")
    print("   - Esperado: 409 y no se crea Servicio.")
    print()
    print("4. Consulta cliente de precotizacion")
    print("   - Precondiciones: servicio ya creado con codigo_precotizacion.")
    print("   - Endpoint: GET /client/services/{service_id}/prequotation")
    print("   - Esperado: 200 con prequotation_code, prequotation_min, prequotation_max y currency=BOB.")


if __name__ == "__main__":
    main()
