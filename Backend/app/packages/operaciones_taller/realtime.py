from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal
from app.models import Incidente, Operario, Servicio, ServicioUbicacion, SolicitudServicio, Taller, Usuario
from app.packages.inteligencia_triaje.matchmaking import haversine_distance_km
from app.packages.seguridad_usuarios.dependencies import (
    get_user_from_access_token,
    resolve_user_tenant_scope,
)
from app.packages.seguridad_usuarios.security import utc_now


logger = logging.getLogger(__name__)
TRACKING_STALE_MINUTES = 5
TRACKING_FALLBACK_SPEED_KMH = Decimal("30")


class WorkshopRealtimeManager:
    def __init__(self) -> None:
        self._service_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._workshop_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def _remember_loop(self) -> None:
        loop = asyncio.get_running_loop()
        if self._loop is None or self._loop.is_closed():
            self._loop = loop

    async def connect_service(self, websocket: WebSocket, service_id: int) -> None:
        self._remember_loop()
        await websocket.accept()
        self._service_connections[service_id].add(websocket)

    async def connect_workshop(self, websocket: WebSocket, workshop_id: int) -> None:
        self._remember_loop()
        await websocket.accept()
        self._workshop_connections[workshop_id].add(websocket)

    async def disconnect_service(self, websocket: WebSocket, service_id: int) -> None:
        connections = self._service_connections.get(service_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._service_connections.pop(service_id, None)

    async def disconnect_workshop(self, websocket: WebSocket, workshop_id: int) -> None:
        connections = self._workshop_connections.get(workshop_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._workshop_connections.pop(workshop_id, None)

    def publish(self, payload: dict[str, Any]) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        future = asyncio.run_coroutine_threadsafe(
            self._broadcast(payload),
            self._loop,
        )
        future.add_done_callback(self._log_future_exception)

    def _log_future_exception(self, future: asyncio.Future[None]) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("Realtime broadcast failed.")

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        encoded_payload = jsonable_encoder(payload)
        service_id = payload.get("service_id")
        workshop_id = payload.get("workshop_id")

        targets: set[WebSocket] = set()
        if isinstance(service_id, int):
            targets.update(self._service_connections.get(service_id, set()))
        if isinstance(workshop_id, int):
            targets.update(self._workshop_connections.get(workshop_id, set()))

        stale: list[WebSocket] = []
        for websocket in tuple(targets):
            try:
                await websocket.send_json(encoded_payload)
            except Exception:
                stale.append(websocket)

        if stale:
            for service_connections in self._service_connections.values():
                for websocket in stale:
                    service_connections.discard(websocket)
            for workshop_connections in self._workshop_connections.values():
                for websocket in stale:
                    workshop_connections.discard(websocket)


realtime_manager = WorkshopRealtimeManager()


def _forbidden(message: str) -> HTTPException:
    return HTTPException(status_code=403, detail=message)


def _serialize_route_points(geometry: Any) -> list[list[float]] | None:
    if isinstance(geometry, dict):
        if geometry.get("type") == "LineString" and isinstance(geometry.get("coordinates"), list):
            points: list[list[float]] = []
            for item in geometry["coordinates"]:
                if isinstance(item, list) and len(item) >= 2:
                    points.append([float(item[1]), float(item[0])])
            return points or None
        return None
    if isinstance(geometry, list):
        points = []
        for item in geometry:
            if isinstance(item, list) and len(item) >= 2:
                points.append([float(item[1]), float(item[0])])
        return points or None
    return None


def _format_operario_name(operario: Operario | None) -> str | None:
    if operario is None or operario.persona is None:
        return None
    persona = operario.persona
    full_name = f"{persona.nombre} {persona.apellido}".strip()
    return full_name or None


def _get_last_location(db: Session, *, service_id: int) -> ServicioUbicacion | None:
    return db.scalar(
        select(ServicioUbicacion)
        .where(ServicioUbicacion.id_servicio == service_id)
        .order_by(ServicioUbicacion.fecha_hora.desc(), ServicioUbicacion.id_ubicacion.desc())
    )


def _get_route_data(db: Session, *, service_id: int) -> ServicioUbicacion | None:
    return db.scalar(
        select(ServicioUbicacion)
        .where(
            ServicioUbicacion.id_servicio == service_id,
            ServicioUbicacion.ruta_geometria.is_not(None),
        )
        .order_by(ServicioUbicacion.fecha_hora.asc(), ServicioUbicacion.id_ubicacion.asc())
    )


def _is_location_stale(location: ServicioUbicacion | None) -> bool:
    if location is None:
        return False
    return location.fecha_hora < utc_now() - timedelta(minutes=TRACKING_STALE_MINUTES)


def _compute_distance_meters(
    *,
    incident_latitud: Decimal | None,
    incident_longitud: Decimal | None,
    location: ServicioUbicacion | None,
) -> Decimal | None:
    if (
        location is None
        or incident_latitud is None
        or incident_longitud is None
    ):
        return None
    distance_km = haversine_distance_km(
        float(location.latitud),
        float(location.longitud),
        float(incident_latitud),
        float(incident_longitud),
    )
    return Decimal(str(distance_km * 1000))


def _estimate_eta_seconds(
    *,
    current_distance_meters: Decimal | None,
    location: ServicioUbicacion | None,
) -> int | None:
    if current_distance_meters is None:
        return None
    speed_kmh = None
    if location is not None and location.velocidad_kmh is not None:
        candidate = Decimal(location.velocidad_kmh)
        if candidate > 0 and candidate <= Decimal("150"):
            speed_kmh = candidate
    if speed_kmh is None:
        speed_kmh = TRACKING_FALLBACK_SPEED_KMH
    if speed_kmh <= 0:
        return None
    distance_km = current_distance_meters / Decimal("1000")
    eta_seconds = (distance_km / speed_kmh) * Decimal("3600")
    return max(int(eta_seconds), 0)


def _format_eta_text(eta_seconds: int | None) -> str | None:
    if eta_seconds is None:
        return None
    if eta_seconds < 60:
        return "Menos de 1 min"
    minutes = max(eta_seconds // 60, 1)
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    remaining = minutes % 60
    if remaining == 0:
        return f"{hours} h"
    return f"{hours} h {remaining} min"


def _load_service(db: Session, service_id: int) -> Servicio | None:
    return db.scalar(
        select(Servicio)
        .options(
            joinedload(Servicio.solicitud)
            .joinedload(SolicitudServicio.incidente)
            .joinedload(Incidente.especialidad_detectada),
            joinedload(Servicio.solicitud).joinedload(SolicitudServicio.taller),
            joinedload(Servicio.operario).joinedload(Operario.persona),
        )
        .where(Servicio.id_servicio == service_id)
    )


def _load_service_snapshot(db: Session, service_id: int) -> dict[str, Any] | None:
    service = _load_service(db, service_id)
    if service is None or service.solicitud is None or service.solicitud.incidente is None:
        return None

    incident = service.solicitud.incidente
    workshop = service.solicitud.taller
    last_location = _get_last_location(db, service_id=service.id_servicio)
    route_data = _get_route_data(db, service_id=service.id_servicio)
    location_stale = _is_location_stale(last_location)
    has_live_location = last_location is not None and not location_stale
    current_distance_meters = _compute_distance_meters(
        incident_latitud=incident.latitud,
        incident_longitud=incident.longitud,
        location=last_location,
    )
    eta_seconds = _estimate_eta_seconds(
        current_distance_meters=current_distance_meters,
        location=last_location,
    )

    return {
        "service": service,
        "incident_id": incident.id_incidente,
        "workshop_id": service.solicitud.id_taller,
        "service_state": service.estado,
        "data": {
            "incident_latitud": incident.latitud,
            "incident_longitud": incident.longitud,
            "operario_latitud": last_location.latitud if last_location is not None else None,
            "operario_longitud": last_location.longitud if last_location is not None else None,
            "route_points": (
                _serialize_route_points(route_data.ruta_geometria)
                if route_data is not None
                else None
            ),
            "route_distance_meters": (
                route_data.ruta_distancia_metros if route_data is not None else None
            ),
            "route_duration_seconds": (
                route_data.ruta_duracion_segundos if route_data is not None else None
            ),
            "last_location_at": last_location.fecha_hora if last_location is not None else None,
            "current_distance_meters": current_distance_meters,
            "eta_seconds": eta_seconds,
            "eta_text": _format_eta_text(eta_seconds),
            "has_live_location": has_live_location,
            "location_stale": location_stale,
            "workshop_name": workshop.nombre_comercial if workshop is not None else None,
            "operario_name": _format_operario_name(service.operario),
            "detected_specialty": (
                incident.especialidad_detectada.nombre
                if incident.especialidad_detectada is not None
                else None
            ),
            "assigned_at": service.fecha_asignacion_operario,
        },
    }


def publish_service_realtime_event(
    *,
    db: Session,
    service_id: int,
    event_type: str,
) -> None:
    snapshot = _load_service_snapshot(db, service_id)
    if snapshot is None:
        return
    realtime_manager.publish(
        {
            "type": event_type,
            "service_id": service_id,
            "incident_id": snapshot["incident_id"],
            "workshop_id": snapshot["workshop_id"],
            "service_state": snapshot["service_state"],
            "timestamp": utc_now(),
            "data": snapshot["data"],
        }
    )


def _authorize_service_subscription(db: Session, user: Usuario, service_id: int) -> None:
    service = _load_service(db, service_id)
    if service is None or service.solicitud is None or service.solicitud.incidente is None:
        raise _forbidden("You do not have access to this service.")

    role = user.tipo_usuario
    if role == "CLIENTE":
        if service.solicitud.incidente.id_cliente != user.id_persona:
            raise _forbidden("You do not have access to this service.")
        return

    if role == "OPERARIO":
        if service.id_persona_operario != user.id_persona:
            raise _forbidden("You do not have access to this service.")
        return

    if role in ("ADMINISTRADOR", "ADMIN_SUCURSAL"):
        administrador = user.persona.administrador if user.persona is not None else None
        if administrador is None or administrador.id_taller != service.solicitud.id_taller:
            raise _forbidden("You do not have access to this service.")
        return

    if role == "ADMIN_GERENTE_SUCURSALES":
        tenant_scope = resolve_user_tenant_scope(user)
        workshop = service.solicitud.taller
        if (
            tenant_scope.tenant_id is None
            or workshop is None
            or workshop.id_tenant != tenant_scope.tenant_id
            or service.solicitud.id_taller not in tenant_scope.workshop_ids
        ):
            raise _forbidden("You do not have access to this service.")
        return

    raise _forbidden("You do not have access to this service.")


def _authorize_workshop_subscription(db: Session, user: Usuario, workshop_id: int) -> None:
    workshop = db.scalar(select(Taller).where(Taller.id_taller == workshop_id))
    if workshop is None:
        raise _forbidden("You do not have access to this workshop.")

    role = user.tipo_usuario
    if role in ("ADMINISTRADOR", "ADMIN_SUCURSAL"):
        administrador = user.persona.administrador if user.persona is not None else None
        if administrador is None or administrador.id_taller != workshop_id:
            raise _forbidden("You do not have access to this workshop.")
        return

    if role == "ADMIN_GERENTE_SUCURSALES":
        tenant_scope = resolve_user_tenant_scope(user)
        if (
            tenant_scope.tenant_id is None
            or workshop.id_tenant != tenant_scope.tenant_id
            or workshop_id not in tenant_scope.workshop_ids
        ):
            raise _forbidden("You do not have access to this workshop.")
        return

    raise _forbidden("You do not have access to this workshop.")


async def serve_service_socket(websocket: WebSocket, service_id: int, token: str) -> None:
    db = SessionLocal()
    try:
        user = get_user_from_access_token(token, db)
        _authorize_service_subscription(db, user, service_id)
        await realtime_manager.connect_service(websocket, service_id)
        while True:
            await websocket.receive_text()
    except (HTTPException, ValueError):
        await websocket.close(code=1008)
    except WebSocketDisconnect:
        pass
    finally:
        await realtime_manager.disconnect_service(websocket, service_id)
        db.close()


async def serve_workshop_tracking_socket(
    websocket: WebSocket,
    workshop_id: int,
    token: str,
) -> None:
    db = SessionLocal()
    try:
        user = get_user_from_access_token(token, db)
        _authorize_workshop_subscription(db, user, workshop_id)
        await realtime_manager.connect_workshop(websocket, workshop_id)
        while True:
            await websocket.receive_text()
    except (HTTPException, ValueError):
        await websocket.close(code=1008)
    except WebSocketDisconnect:
        pass
    finally:
        await realtime_manager.disconnect_workshop(websocket, workshop_id)
        db.close()
