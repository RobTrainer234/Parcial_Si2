from __future__ import annotations

NOTIFICATION_TYPE_SOLICITUD_NUEVA = "SOLICITUD_NUEVA"
NOTIFICATION_TYPE_SOLICITUD_ACEPTADA = "SOLICITUD_ACEPTADA"
NOTIFICATION_TYPE_OPERARIO_ASIGNADO = "OPERARIO_ASIGNADO"
NOTIFICATION_TYPE_OPERARIO_EN_CAMINO = "OPERARIO_EN_CAMINO"
NOTIFICATION_TYPE_OPERARIO_LLEGO = "OPERARIO_LLEGO"
NOTIFICATION_TYPE_SERVICIO_INICIADO = "SERVICIO_INICIADO"
NOTIFICATION_TYPE_SERVICIO_FINALIZADO = "SERVICIO_FINALIZADO"
NOTIFICATION_TYPE_PAGO_PENDIENTE = "PAGO_PENDIENTE"
NOTIFICATION_TYPE_PAGO_CONFIRMADO = "PAGO_CONFIRMADO"
NOTIFICATION_TYPE_CALIFICACION_PENDIENTE = "CALIFICACION_PENDIENTE"
NOTIFICATION_TYPE_GENERAL = "GENERAL"

ALL_NOTIFICATION_TYPES = frozenset({
    NOTIFICATION_TYPE_SOLICITUD_NUEVA,
    NOTIFICATION_TYPE_SOLICITUD_ACEPTADA,
    NOTIFICATION_TYPE_OPERARIO_ASIGNADO,
    NOTIFICATION_TYPE_OPERARIO_EN_CAMINO,
    NOTIFICATION_TYPE_OPERARIO_LLEGO,
    NOTIFICATION_TYPE_SERVICIO_INICIADO,
    NOTIFICATION_TYPE_SERVICIO_FINALIZADO,
    NOTIFICATION_TYPE_PAGO_PENDIENTE,
    NOTIFICATION_TYPE_PAGO_CONFIRMADO,
    NOTIFICATION_TYPE_CALIFICACION_PENDIENTE,
    NOTIFICATION_TYPE_GENERAL,
})

NOTIFICATION_ROLE_OPERARIO = "OPERARIO"
NOTIFICATION_ROLE_CLIENTE = "CLIENTE"
NOTIFICATION_ROLE_ADMIN = "ADMIN"


def _resolve_role(tipo_usuario: str) -> str:
    t = tipo_usuario.strip().upper()
    if t == "OPERARIO":
        return NOTIFICATION_ROLE_OPERARIO
    if t in ("ADMINISTRADOR", "ADMIN_SUCURSAL", "ADMIN_GERENTE_SUCURSALES"):
        return NOTIFICATION_ROLE_ADMIN
    return NOTIFICATION_ROLE_CLIENTE


def build_notification_route(
    *,
    notification_type: str,
    service_id: int | None = None,
    incident_id: int | None = None,
    request_id: int | None = None,
    user_tipo: str = "CLIENTE",
) -> str | None:
    role = _resolve_role(user_tipo)

    if notification_type == NOTIFICATION_TYPE_OPERARIO_ASIGNADO:
        if role == NOTIFICATION_ROLE_OPERARIO and service_id is not None:
            return f"/operario/services/{service_id}"
        if service_id is not None:
            return f"/services/{service_id}/tracking"

    if notification_type in (
        NOTIFICATION_TYPE_OPERARIO_EN_CAMINO,
        NOTIFICATION_TYPE_OPERARIO_LLEGO,
        NOTIFICATION_TYPE_SERVICIO_INICIADO,
    ):
        if role == NOTIFICATION_ROLE_CLIENTE and service_id is not None:
            return f"/services/{service_id}/tracking"

    if notification_type == NOTIFICATION_TYPE_SERVICIO_FINALIZADO:
        if role == NOTIFICATION_ROLE_CLIENTE and service_id is not None:
            return f"/services/{service_id}/finalization"

    if notification_type == NOTIFICATION_TYPE_PAGO_PENDIENTE:
        if role == NOTIFICATION_ROLE_CLIENTE and service_id is not None:
            return f"/services/{service_id}/payment"

    if notification_type in (
        NOTIFICATION_TYPE_PAGO_CONFIRMADO,
        NOTIFICATION_TYPE_CALIFICACION_PENDIENTE,
    ):
        if role == NOTIFICATION_ROLE_CLIENTE and service_id is not None:
            return f"/services/{service_id}/rating"

    if notification_type == NOTIFICATION_TYPE_SOLICITUD_ACEPTADA:
        if service_id is not None:
            if role == NOTIFICATION_ROLE_CLIENTE:
                return f"/services/{service_id}/prequotation"
            if role == NOTIFICATION_ROLE_ADMIN:
                return f"/admin/services/{service_id}/assign-operario"

    return None
