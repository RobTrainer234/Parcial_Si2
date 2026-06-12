from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Notificacion, Usuario
from app.packages.seguridad_usuarios.dependencies import ensure_user_login_allowed, user_context_query
from app.packages.seguridad_usuarios.security import decode_token


router = APIRouter(tags=["realtime"])


def _serialize_notification(notification: Notificacion) -> dict[str, Any]:
    payload = notification.payload if isinstance(notification.payload, dict) else {}
    return {
        "event": "notification.created",
        "transport": "websocket",
        "notification_id": notification.id_notificacion,
        "service_id": notification.id_servicio,
        "request_id": notification.id_solicitud,
        "channel": notification.canal,
        "title": notification.titulo,
        "message": notification.mensaje,
        "payload": notification.payload,
        "status": notification.estado,
        "provider": notification.proveedor,
        "created_at": notification.fecha_creacion.isoformat(),
        "sent_at": notification.fecha_envio.isoformat() if notification.fecha_envio else None,
        "read_at": notification.fecha_lectura.isoformat() if notification.fecha_lectura else None,
        "type": payload.get("type"),
        "entity_type": payload.get("entity_type"),
        "entity_id": payload.get("entity_id"),
        "route_suggested": payload.get("route_suggested"),
    }


def _authenticate_websocket(token: str) -> Usuario | None:
    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
    except Exception:
        return None

    with SessionLocal() as db:
        user = db.scalar(user_context_query().where(Usuario.id_usuario == user_id))
        if user is None:
            return None
        try:
            ensure_user_login_allowed(user)
        except Exception:
            return None
        db.expunge(user)
        return user


def _notifications_after(*, user_id: int, cursor: int) -> list[Notificacion]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(Notificacion)
                .where(
                    Notificacion.id_usuario == user_id,
                    Notificacion.id_notificacion > cursor,
                )
                .order_by(Notificacion.id_notificacion.asc())
                .limit(50)
            )
        )


@router.websocket("/realtime/ws")
async def realtime_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    user = _authenticate_websocket(token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid access token")
        return

    try:
        cursor = max(int(websocket.query_params.get("cursor", "0")), 0)
    except ValueError:
        cursor = 0

    await websocket.accept()
    await websocket.send_json(
        {
            "event": "connection.ready",
            "transport": "websocket",
            "user_id": user.id_usuario,
            "cursor": cursor,
            "message": "Real-time channel connected. Push remains the background channel.",
        }
    )

    heartbeat_at = asyncio.get_running_loop().time()
    try:
        while True:
            notifications = await asyncio.to_thread(
                _notifications_after,
                user_id=user.id_usuario,
                cursor=cursor,
            )
            for notification in notifications:
                await websocket.send_json(_serialize_notification(notification))
                cursor = notification.id_notificacion

            now = asyncio.get_running_loop().time()
            if now - heartbeat_at >= 15:
                await websocket.send_json(
                    {
                        "event": "connection.heartbeat",
                        "transport": "websocket",
                        "cursor": cursor,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                heartbeat_at = now
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
    except RuntimeError:
        return
