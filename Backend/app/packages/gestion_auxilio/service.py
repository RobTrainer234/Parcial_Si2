from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.models import (
    Administrador,
    Bitacora,
    CatalogoServicioTaller,
    DispositivoUsuario,
    Evidencia,
    Incidente,
    Notificacion,
    Operario,
    Seguro,
    Servicio,
    ServicioUbicacion,
    SolicitudServicio,
    TipoCobertura,
    Usuario,
)
from app.packages.inteligencia_triaje.matchmaking import build_ranked_candidate
from app.packages.inteligencia_triaje.diagnosis_utils import (
    build_triage_details_from_payload,
)
from app.packages.inteligencia_triaje.service import (
    _build_ranked_candidates,
    _get_attempted_workshop_ids,
)
from app.packages.inteligencia_triaje.matchmaking import haversine_distance_km
from app.packages.seguridad_usuarios.security import utc_now

from .maps_provider import RouteProviderError, get_route
from .notification_types import (
    NOTIFICATION_TYPE_OPERARIO_EN_CAMINO,
    build_notification_route,
)
from .push_provider import PushProviderError, send_push_notification
from .schemas import (
    ClientActiveServiceSummaryResponse,
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    DeviceUnregisterRequest,
    DispatchPendingResponse,
    NavigationStartRequest,
    NavigationStartResponse,
    NavigationStatusResponse,
    FinalizationDecisionRequest,
    FinalizationDecisionResponse,
    FinalizationRequestResponse,
    FinalizationStatusResponse,
    FinalizationTimelineItem,
    HireWorkshopRequest,
    HireWorkshopResponse,
    IncidentDiagnosisSummaryResponse,
    IncidentRecommendationsResponse,
    MarkAllReadResponse,
    RecommendedWorkshopResponse,
    ServicePrequotationResponse,
    NotificationInboxItem,
    NotificationReadResponse,
    RouteStepSummary,
    ServiceProgressHistoryItem,
    ServiceProgressSnapshotResponse,
    ServiceProgressUpdateRequest,
    ServiceProgressUpdateResponse,
    TrackingHistoryPointResponse,
    TrackingStatusResponse,
    UnreadCountResponse,
    ServiceLocationUpdateRequest,
    ServiceLocationUpdateResponse,
)


settings = get_settings()
logger = logging.getLogger(__name__)
NAVIGATION_START_ALLOWED_STATES = {"ASIGNADO", "EN_CAMINO"}
NAVIGATION_STATUS_ALLOWED_STATES = {
    "ASIGNADO",
    "EN_CAMINO",
    "EN_SITIO",
    "EN_DIAGNOSTICO_FISICO",
    "EN_REPARACION",
    "ESPERANDO_REPUESTOS",
}
PROGRESS_ALLOWED_STATES = {
    "ASIGNADO",
    "EN_CAMINO",
    "EN_SITIO",
    "EN_DIAGNOSTICO_FISICO",
    "EN_REPARACION",
    "ESPERANDO_REPUESTOS",
}
PROGRESS_TRANSITIONS: dict[str, set[str]] = {
    "EN_CAMINO": {"EN_SITIO"},
    "EN_SITIO": {"EN_DIAGNOSTICO_FISICO"},
    "EN_DIAGNOSTICO_FISICO": {"EN_REPARACION", "ESPERANDO_REPUESTOS"},
    "EN_REPARACION": {"ESPERANDO_REPUESTOS"},
    "ESPERANDO_REPUESTOS": {"EN_REPARACION"},
}
PROGRESS_TIMELINE_ACTIONS = {
    "NAVEGACION_INICIADA",
    "OPERARIO_EN_SITIO",
    "SERVICIO_ESTADO_ACTUALIZADO",
}
FINALIZATION_PENDING_STATE = "COMPLETADO_PENDIENTE_CONFIRMACION"
FINALIZATION_CONFIRMED_STATE = "FINALIZADO_PENDIENTE_PAGO"
FINALIZATION_REWORK_STATE = "EN_REPARACION"
FINALIZATION_TIMELINE_ACTIONS = {
    "SERVICIO_LISTO_PARA_VALIDACION",
    "FINALIZACION_SOLICITADA",
    "FINALIZACION_CONFIRMADA_CLIENTE",
    "FINALIZACION_RECHAZADA_CLIENTE",
}
TRACKING_ALLOWED_STATES = {
    "EN_ESPERA_ASIGNACION",
    "ASIGNADO",
    "EN_CAMINO",
    "EN_SITIO",
    "EN_DIAGNOSTICO_FISICO",
    "EN_REPARACION",
    "ESPERANDO_REPUESTOS",
    "COMPLETADO_PENDIENTE_CONFIRMACION",
    "FINALIZADO_PENDIENTE_PAGO",
    "PAGADO",
}
TRACKING_STALE_MINUTES = 5
TRACKING_FALLBACK_SPEED_KMH = Decimal("30")
TRACKING_HISTORY_LIMIT = 20
NOTIFICATION_INBOX_LIMIT = 50
NOTIFICATION_SENDABLE_STATES = {"PENDIENTE", "FALLIDA"}
RECOMMENDATION_MATCHMAKING_ACTIONS = {
    "MATCHMAKING_INICIADO",
    "MATCHMAKING_SIN_CANDIDATOS",
    "MATCHMAKING_CANDIDATO_SELECCIONADO",
    "SOLICITUD_SERVICIO_CREADA",
}
PREQUOTATION_CURRENCY = "BOB"
CLIENT_ACTIVE_SERVICE_STATES = {
    "EN_ESPERA_ASIGNACION",
    "ASIGNADO",
    "EN_CAMINO",
    "EN_SITIO",
    "EN_DIAGNOSTICO_FISICO",
    "EN_REPARACION",
    "ESPERANDO_REPUESTOS",
    "COMPLETADO_PENDIENTE_CONFIRMACION",
    "FINALIZADO_PENDIENTE_PAGO",
    "PAGADO",
}


def _build_service_query():
    return select(Servicio).options(
        joinedload(Servicio.operario).joinedload(Operario.persona),
        joinedload(Servicio.informe),
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.incidente)
        .joinedload(Incidente.especialidad_detectada),
        joinedload(Servicio.solicitud).joinedload(SolicitudServicio.taller),
        selectinload(Servicio.evidencias),
    )


def _build_incident_recommendations_query():
    return select(Incidente).options(
        joinedload(Incidente.especialidad_reportada_cliente),
        joinedload(Incidente.especialidad_detectada),
        selectinload(Incidente.solicitudes).joinedload(SolicitudServicio.taller),
    )


def _normalize_catalog_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).upper()
    return normalized or None


def _get_assigned_service(
    db: Session,
    *,
    service_id: int,
    operario_id: int,
) -> Servicio:
    service = db.scalar(
        _build_service_query().where(
            Servicio.id_servicio == service_id,
            Servicio.id_persona_operario == operario_id,
        )
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned service not found.",
        )
    return service


def _get_client_owned_service(
    db: Session,
    *,
    service_id: int,
    cliente_id: int,
) -> Servicio:
    service = db.scalar(
        _build_service_query()
        .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
        .join(Incidente, Incidente.id_incidente == SolicitudServicio.id_incidente)
        .where(
            Servicio.id_servicio == service_id,
            Incidente.id_cliente == cliente_id,
        )
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client service not found.",
        )
    return service


def _get_latest_service_prequotation_payload(
    db: Session,
    *,
    service_id: int,
) -> dict[str, object] | None:
    event = db.scalar(
        select(Bitacora)
        .where(
            Bitacora.id_servicio == service_id,
            Bitacora.accion == "PRECOTIZACION_TECNICA_GENERADA",
        )
        .order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
    )
    if event is None or not isinstance(event.datos_nuevos, dict):
        return None
    return event.datos_nuevos


def _get_client_owned_incident(
    db: Session,
    *,
    incident_id: int,
    cliente_id: int,
) -> Incidente:
    incident = db.scalar(
        _build_incident_recommendations_query().where(
            Incidente.id_incidente == incident_id,
            Incidente.id_cliente == cliente_id,
        )
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )
    return incident


def _validate_recommendations_diagnosis_ready(incident: Incidente) -> None:
    if (
        incident.fecha_triaje is None
        or incident.id_especialidad_detectada is None
        or incident.severidad is None
        or (incident.diagnostico_ia_resumen is None and incident.diagnostico_ia_json is None)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident diagnosis is not ready for recommendations.",
        )


def _has_matchmaking_history(
    db: Session,
    *,
    incident_id: int,
) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    Bitacora.id_incidente == incident_id,
                    Bitacora.accion.in_(tuple(RECOMMENDATION_MATCHMAKING_ACTIONS)),
                )
            )
        )
    )


def _validate_navigation_status_eligible(service: Servicio) -> Incidente:
    if service.estado not in NAVIGATION_STATUS_ALLOWED_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not in a navigation-compatible state.",
        )
    return service.solicitud.incidente


def _validate_progress_eligible(service: Servicio) -> Incidente:
    if service.estado not in PROGRESS_ALLOWED_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not in a progress-compatible state.",
        )
    return service.solicitud.incidente


def _validate_tracking_eligible(service: Servicio) -> Incidente:
    if service.estado not in TRACKING_ALLOWED_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not in a tracking-compatible state.",
        )
    return service.solicitud.incidente


def _validate_navigation_start_eligible(
    *,
    service: Servicio,
    incident: Incidente,
    current_user: Usuario,
    db: Session,
) -> None:
    if service.estado not in NAVIGATION_START_ALLOWED_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not ready to start navigation.",
        )
    if incident.latitud is None or incident.longitud is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident destination coordinates are not available.",
        )
    if not db.scalar(
        select(
            exists().where(
                Bitacora.id_servicio == service.id_servicio,
                Bitacora.accion == "PERFIL_FALLA_ESTRUCTURADO_ACK",
                Bitacora.id_usuario == current_user.id_usuario,
            )
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Structured profile must be acknowledged before navigation starts.",
        )


def _create_navigation_bitacora(
    *,
    current_user: Usuario,
    service: Servicio,
    incident: Incidente,
    accion: str,
    descripcion: str,
    datos_nuevos: dict[str, object] | None,
    ip_origen: str | None,
    user_agent: str | None,
) -> Bitacora:
    return Bitacora(
        accion=accion,
        tipo_evento="OPERACION_CAMPO",
        descripcion=descripcion,
        entidad_principal="SERVICIO",
        id_entidad_principal=service.id_servicio,
        datos_nuevos=datos_nuevos,
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=current_user.id_usuario,
        id_incidente=incident.id_incidente,
        id_solicitud=service.id_solicitud,
        id_servicio=service.id_servicio,
    )


def _persist_location_point(
    *,
    db: Session,
    service: Servicio,
    latitud: Decimal,
    longitud: Decimal,
    accuracy_meters: Decimal | None,
    speed_mps: Decimal | None,
    device_timestamp,
    route_data: dict[str, object] | None = None,
) -> ServicioUbicacion:
    location = ServicioUbicacion(
        id_servicio=service.id_servicio,
        id_persona_operario=service.id_persona_operario,
        latitud=latitud,
        longitud=longitud,
        precision_metros=accuracy_meters,
        velocidad_kmh=(
            speed_mps * Decimal("3.6") if speed_mps is not None else None
        ),
        fecha_hora=device_timestamp or utc_now(),
    )
    if route_data:
        location.ruta_origen_latitud = route_data.get("origin_lat")
        location.ruta_origen_longitud = route_data.get("origin_lon")
        location.ruta_destino_latitud = route_data.get("dest_lat")
        location.ruta_destino_longitud = route_data.get("dest_lon")
        location.ruta_distancia_metros = route_data.get("distance_meters")
        location.ruta_duracion_segundos = route_data.get("duration_seconds")
        location.ruta_geometria = route_data.get("geometry")
    db.add(location)
    db.flush()
    return location


def _distance_to_incident_meters(*, incident: Incidente, latitud: Decimal, longitud: Decimal) -> Decimal:
    return haversine_distance_km(
        lat1=latitud,
        lon1=longitud,
        lat2=incident.latitud,
        lon2=incident.longitud,
    ) * Decimal("1000")


def _get_client_user(db: Session, *, cliente_id: int) -> Usuario:
    client_user = db.scalar(select(Usuario).where(Usuario.id_persona == cliente_id))
    if client_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Incident client account is not provisioned.",
        )
    return client_user


def _get_operario_user(db: Session, *, operario_id: int | None) -> Usuario:
    if operario_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assigned operario account is not provisioned.",
        )
    operario_user = db.scalar(select(Usuario).where(Usuario.id_persona == operario_id))
    if operario_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assigned operario account is not provisioned.",
        )
    return operario_user


def _get_workshop_admin_users(db: Session, *, workshop_id: int) -> list[Usuario]:
    return list(
        db.scalars(
            select(Usuario)
            .join(Administrador, Administrador.id_persona == Usuario.id_persona)
            .where(
                Administrador.id_taller == workshop_id,
                Administrador.activo.is_(True),
                Usuario.activo.is_(True),
            )
            .order_by(Usuario.id_usuario)
        )
    )


def _is_profile_acknowledged(
    *,
    db: Session,
    service_id: int,
    user_id: int,
) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    Bitacora.id_servicio == service_id,
                    Bitacora.accion == "PERFIL_FALLA_ESTRUCTURADO_ACK",
                    Bitacora.id_usuario == user_id,
                )
            )
        )
    )


def _create_service_notification(
    *,
    db: Session,
    user: Usuario,
    service: Servicio,
    title: str,
    message: str,
    payload: dict[str, object],
) -> None:
    db.add(
        Notificacion(
            id_usuario=user.id_usuario,
            id_servicio=service.id_servicio,
            id_solicitud=service.id_solicitud,
            canal="WEB",
            titulo=title,
            mensaje=message,
            payload=payload,
            estado="PENDIENTE",
        )
    )


def _create_notification_bitacora(
    *,
    current_user: Usuario,
    accion: str,
    descripcion: str,
    entidad_principal: str,
    id_entidad_principal: int | None,
    datos_nuevos: dict[str, object] | None,
    notification: Notificacion | None = None,
    ip_origen: str | None,
    user_agent: str | None,
) -> Bitacora:
    return Bitacora(
        accion=accion,
        tipo_evento="NOTIFICACION",
        descripcion=descripcion,
        entidad_principal=entidad_principal,
        id_entidad_principal=id_entidad_principal,
        datos_nuevos=datos_nuevos,
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=current_user.id_usuario,
        id_incidente=None,
        id_solicitud=notification.id_solicitud if notification is not None else None,
        id_servicio=notification.id_servicio if notification is not None else None,
    )


def _create_typed_notification(
    *,
    db: Session,
    user: Usuario,
    notification_type: str,
    title: str,
    message: str,
    service: Servicio | None = None,
    request_id: int | None = None,
    incident_id: int | None = None,
    extra_payload: dict[str, object] | None = None,
    canal: str = "PUSH",
) -> Notificacion:
    entity_type: str | None = None
    entity_id: int | None = None
    if service is not None:
        entity_type = "servicio"
        entity_id = service.id_servicio
        if request_id is None:
            request_id = service.id_solicitud
    elif request_id is not None:
        entity_type = "solicitud"
        entity_id = request_id

    payload: dict[str, object] = {
        "type": notification_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
    }
    if extra_payload:
        for k, v in extra_payload.items():
            if k not in payload:
                payload[k] = v
    if service is not None:
        payload.setdefault("service_id", service.id_servicio)
        payload.setdefault("service_state", service.estado)

    payload["route_suggested"] = build_notification_route(
        notification_type=notification_type,
        service_id=entity_id if entity_type == "servicio" else None,
        incident_id=incident_id,
        request_id=request_id,
        user_tipo=user.tipo_usuario,
    )

    notification = Notificacion(
        id_usuario=user.id_usuario,
        id_servicio=service.id_servicio if service is not None else None,
        id_solicitud=request_id,
        canal=canal,
        titulo=title,
        mensaje=message,
        payload=payload,
        estado="PENDIENTE",
    )
    db.add(notification)
    return notification


def _auto_dispatch_notifications(
    *,
    target_user: Usuario,
    db: Session,
) -> None:
    try:
        devices = _get_active_user_devices(db, user_id=target_user.id_usuario)
        if not devices:
            return
        notifications = _get_sendable_notifications(db, user_id=target_user.id_usuario)
        if not notifications:
            return
        device_tokens = [device.token_push for device in devices]
        for notification in notifications:
            push_payload: dict[str, object] = {
                "notification_id": notification.id_notificacion,
            }
            if isinstance(notification.payload, dict):
                push_payload.update(notification.payload)
            try:
                result = send_push_notification(
                    device_tokens=device_tokens,
                    title=notification.titulo,
                    message=notification.mensaje,
                    payload=push_payload,
                )
            except PushProviderError:
                notification.estado = "FALLIDA"
                notification.proveedor = settings.push_provider
                db.add(notification)
                continue
            invalid_set = set(result.invalid_tokens)
            for device in devices:
                if device.token_push in invalid_set and device.activo:
                    device.activo = False
                    device.ultimo_registro = utc_now()
                    db.add(device)
            if result.success:
                notification.estado = "ENVIADA"
                notification.fecha_envio = notification.fecha_envio or utc_now()
                notification.proveedor = result.provider
            else:
                notification.estado = "FALLIDA"
                notification.proveedor = result.provider
            db.add(notification)
        db.commit()
    except Exception:
        db.rollback()


def _get_user_device_by_token(
    db: Session,
    *,
    token_push: str,
) -> DispositivoUsuario | None:
    return db.scalar(
        select(DispositivoUsuario).where(DispositivoUsuario.token_push == token_push)
    )


def _get_active_user_devices(
    db: Session,
    *,
    user_id: int,
) -> list[DispositivoUsuario]:
    return list(
        db.scalars(
            select(DispositivoUsuario)
            .where(
                DispositivoUsuario.id_usuario == user_id,
                DispositivoUsuario.activo.is_(True),
            )
            .order_by(
                DispositivoUsuario.ultimo_registro.desc(),
                DispositivoUsuario.id_dispositivo.desc(),
            )
        )
    )


def _get_user_notification(
    db: Session,
    *,
    notification_id: int,
    user_id: int,
) -> Notificacion:
    notification = db.scalar(
        select(Notificacion).where(
            Notificacion.id_notificacion == notification_id,
            Notificacion.id_usuario == user_id,
        )
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return notification


def _serialize_notification_item(notification: Notificacion) -> NotificationInboxItem:
    payload = notification.payload
    notification_type = None
    entity_type = None
    entity_id = None
    route_suggested = None
    if isinstance(payload, dict):
        notification_type = payload.get("type")
        entity_type = payload.get("entity_type")
        eid = payload.get("entity_id")
        if isinstance(eid, int):
            entity_id = eid
        route_suggested = payload.get("route_suggested")

    return NotificationInboxItem(
        notification_id=notification.id_notificacion,
        service_id=notification.id_servicio,
        request_id=notification.id_solicitud,
        channel=notification.canal,
        title=notification.titulo,
        message=notification.mensaje,
        payload=payload,
        status=notification.estado,
        provider=notification.proveedor,
        created_at=notification.fecha_creacion,
        sent_at=notification.fecha_envio,
        read_at=notification.fecha_lectura,
        type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        route_suggested=route_suggested,
    )


def _get_sendable_notifications(
    db: Session,
    *,
    user_id: int,
) -> list[Notificacion]:
    return list(
        db.scalars(
            select(Notificacion)
            .where(
                Notificacion.id_usuario == user_id,
                Notificacion.estado.in_(tuple(NOTIFICATION_SENDABLE_STATES)),
                Notificacion.canal.in_(("WEB", "PUSH")),
            )
            .order_by(
                Notificacion.fecha_creacion.asc(),
                Notificacion.id_notificacion.asc(),
            )
        )
    )


def _deactivate_invalid_devices(
    *,
    db: Session,
    current_user: Usuario,
    devices: list[DispositivoUsuario],
    invalid_tokens: tuple[str, ...],
    ip_origen: str | None,
    user_agent: str | None,
) -> int:
    invalid_set = set(invalid_tokens)
    deactivated = 0
    for device in devices:
        if device.token_push not in invalid_set or not device.activo:
            continue
        device.activo = False
        device.ultimo_registro = utc_now()
        deactivated += 1
        db.add(
            _create_notification_bitacora(
                current_user=current_user,
                accion="DISPOSITIVO_NOTIFICACION_DESACTIVADO",
                descripcion="Se desactivo un dispositivo con token push invalido.",
                entidad_principal="USUARIO",
                id_entidad_principal=current_user.id_usuario,
                datos_nuevos={
                    "device_id": device.id_dispositivo,
                    "platform": device.plataforma,
                    "reason": "invalid_token",
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )
    return deactivated


def _build_progress_timeline_item(event: Bitacora) -> ServiceProgressHistoryItem:
    datos = event.datos_nuevos or {}
    previous_state = None
    new_state = None
    observacion = None
    if isinstance(datos, dict):
        previous_state = datos.get("previous_state")
        new_state = datos.get("new_state") or datos.get("service_state")
        observacion = datos.get("observacion")
    return ServiceProgressHistoryItem(
        timestamp=event.fecha_hora,
        action=event.accion,
        previous_state=previous_state,
        new_state=new_state,
        observacion=observacion,
    )


def _get_progress_timeline(
    db: Session,
    *,
    service_id: int,
    limit: int | None = None,
) -> list[ServiceProgressHistoryItem]:
    query = (
        select(Bitacora)
        .where(
            Bitacora.id_servicio == service_id,
            Bitacora.accion.in_(tuple(PROGRESS_TIMELINE_ACTIONS)),
        )
        .order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    events = list(db.scalars(query))
    items = [_build_progress_timeline_item(item) for item in reversed(events)]
    return items


def _get_allowed_next_states(current_state: str) -> list[str]:
    return sorted(PROGRESS_TRANSITIONS.get(current_state, set()))


def _get_final_evidence_count(service: Servicio) -> int:
    return sum(
        1
        for evidence in service.evidencias
        if evidence.id_servicio == service.id_servicio and evidence.categoria == "CIERRE"
    )


def _is_finalization_request_eligible(service: Servicio) -> bool:
    return service.estado == FINALIZATION_PENDING_STATE and service.informe is not None


def _validate_finalization_request_eligible(service: Servicio) -> Incidente:
    if service.estado != FINALIZATION_PENDING_STATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not ready for a finalization request.",
        )
    if service.informe is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repair report must exist before requesting finalization.",
        )
    return service.solicitud.incidente


def _validate_finalization_decision_eligible(service: Servicio) -> Incidente:
    if service.estado != FINALIZATION_PENDING_STATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not awaiting client finalization.",
        )
    if service.informe is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repair report must exist before client finalization.",
        )
    return service.solicitud.incidente


def _build_finalization_timeline_item(event: Bitacora) -> FinalizationTimelineItem:
    datos = event.datos_nuevos or {}
    previous_state = None
    new_state = None
    motivo = None
    duration_seconds = None
    if isinstance(datos, dict):
        previous_state = datos.get("previous_state")
        new_state = datos.get("new_state") or datos.get("service_state")
        motivo = datos.get("motivo")
        raw_duration = datos.get("duration_seconds")
        if raw_duration is not None:
            try:
                duration_seconds = int(raw_duration)
            except (TypeError, ValueError):
                duration_seconds = None
    return FinalizationTimelineItem(
        timestamp=event.fecha_hora,
        action=event.accion,
        previous_state=previous_state,
        new_state=new_state,
        motivo=motivo,
        duration_seconds=duration_seconds,
    )


def _get_finalization_timeline(
    db: Session,
    *,
    service_id: int,
    limit: int = 10,
) -> list[FinalizationTimelineItem]:
    events = list(
        db.scalars(
            select(Bitacora)
            .where(
                Bitacora.id_servicio == service_id,
                Bitacora.accion.in_(tuple(FINALIZATION_TIMELINE_ACTIONS)),
            )
            .order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
            .limit(limit)
        )
    )
    return [_build_finalization_timeline_item(item) for item in reversed(events)]


def _has_pending_finalization_request(db: Session, *, service: Servicio) -> bool:
    if service.estado != FINALIZATION_PENDING_STATE:
        return False
    if service.confirmacion_cliente is not None:
        return False

    latest_event = db.scalar(
        select(Bitacora)
        .where(
            Bitacora.id_servicio == service.id_servicio,
            Bitacora.accion.in_(
                (
                    "SERVICIO_LISTO_PARA_VALIDACION",
                    "FINALIZACION_SOLICITADA",
                    "FINALIZACION_CONFIRMADA_CLIENTE",
                    "FINALIZACION_RECHAZADA_CLIENTE",
                )
            ),
        )
        .order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
    )
    return latest_event is not None and latest_event.accion == "FINALIZACION_SOLICITADA"


def _build_finalization_status(service: Servicio) -> FinalizationStatusResponse:
    incident = service.solicitud.incidente
    return FinalizationStatusResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        report_exists=service.informe is not None,
        final_evidence_count=_get_final_evidence_count(service),
        finalization_eligible=_is_finalization_request_eligible(service),
        client_decision_pending=service.estado == FINALIZATION_PENDING_STATE,
        confirmed_at=(
            service.fecha_confirmacion_cliente if service.confirmacion_cliente is True else None
        ),
        timeline=[],
    )


def _compute_service_duration_seconds(service: Servicio) -> int | None:
    if service.fecha_inicio is None or service.fecha_fin is None:
        return None
    delta = service.fecha_fin - service.fecha_inicio
    return max(int(delta.total_seconds()), 0)


def _arrival_already_recorded(db: Session, *, service_id: int) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    Bitacora.id_servicio == service_id,
                    Bitacora.accion == "OPERARIO_EN_SITIO",
                )
            )
        )
    )


def _mark_arrival_if_needed(
    *,
    db: Session,
    service: Servicio,
    incident: Incidente,
    current_user: Usuario,
    current_distance_meters: Decimal,
    ip_origen: str | None,
    user_agent: str | None,
) -> bool:
    threshold = Decimal(settings.navigation_arrival_threshold_meters)
    if current_distance_meters > threshold:
        return False
    if service.estado == "EN_SITIO" or _arrival_already_recorded(db, service_id=service.id_servicio):
        service.estado = "EN_SITIO"
        return True

    service.estado = "EN_SITIO"
    client_user = _get_client_user(db, cliente_id=incident.id_cliente)
    db.add(
        _create_navigation_bitacora(
            current_user=current_user,
            service=service,
            incident=incident,
            accion="OPERARIO_EN_SITIO",
            descripcion="El operario llego al sitio del incidente.",
            datos_nuevos={
                "service_state": service.estado,
                "distance_meters": str(current_distance_meters),
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    from .notification_types import NOTIFICATION_TYPE_OPERARIO_LLEGO

    _create_typed_notification(
        db=db,
        user=client_user,
        notification_type=NOTIFICATION_TYPE_OPERARIO_LLEGO,
        title="Operario en sitio",
        message="El operario ya llego a la ubicacion del incidente.",
        service=service,
        incident_id=incident.id_incidente,
    )
    return True


def _get_route_data(
    db: Session,
    *,
    service_id: int,
) -> ServicioUbicacion | None:
    return db.scalar(
        select(ServicioUbicacion)
        .where(
            ServicioUbicacion.id_servicio == service_id,
            ServicioUbicacion.ruta_geometria.is_not(None),
        )
        .order_by(ServicioUbicacion.fecha_hora.asc(), ServicioUbicacion.id_ubicacion.asc())
    )


def _get_last_location(
    db: Session,
    *,
    service_id: int,
) -> ServicioUbicacion | None:
    return db.scalar(
        select(ServicioUbicacion)
        .where(ServicioUbicacion.id_servicio == service_id)
        .order_by(ServicioUbicacion.fecha_hora.desc(), ServicioUbicacion.id_ubicacion.desc())
    )


def _get_recent_tracking_points(
    db: Session,
    *,
    service_id: int,
    limit: int = TRACKING_HISTORY_LIMIT,
) -> list[ServicioUbicacion]:
    points = list(
        db.scalars(
            select(ServicioUbicacion)
            .where(ServicioUbicacion.id_servicio == service_id)
            .order_by(ServicioUbicacion.fecha_hora.desc(), ServicioUbicacion.id_ubicacion.desc())
            .limit(limit)
        )
    )
    return list(reversed(points))


def _is_location_stale(location: ServicioUbicacion | None) -> bool:
    if location is None:
        return False
    now = utc_now()
    return location.fecha_hora < now - timedelta(minutes=TRACKING_STALE_MINUTES)


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


def _get_active_incident_request(incident: Incidente) -> SolicitudServicio | None:
    active_requests = [
        item
        for item in incident.solicitudes
        if item.es_actual and item.estado in {"PENDIENTE", "ACEPTADA"}
    ]
    if not active_requests:
        return None
    active_requests.sort(
        key=lambda item: (item.intento_numero, item.id_solicitud),
        reverse=True,
    )
    return active_requests[0]


def _get_latest_request_by_workshop(
    incident: Incidente,
) -> dict[int, SolicitudServicio]:
    latest_by_workshop: dict[int, SolicitudServicio] = {}
    for request_row in incident.solicitudes:
        existing = latest_by_workshop.get(request_row.id_taller)
        if existing is None or (
            request_row.intento_numero,
            request_row.id_solicitud,
        ) > (
            existing.intento_numero,
            existing.id_solicitud,
        ):
            latest_by_workshop[request_row.id_taller] = request_row
    return latest_by_workshop


def _get_active_insurance_map(
    db: Session,
    *,
    cliente_id: int,
    workshop_ids: set[int],
) -> dict[int, list[Seguro]]:
    if not workshop_ids:
        return {}

    now = utc_now()
    insurances = list(
        db.scalars(
            select(Seguro)
            .options(
                joinedload(Seguro.cobertura).selectinload(TipoCobertura.especialidades)
            )
            .where(
                Seguro.id_cliente == cliente_id,
                Seguro.activo.is_(True),
                Seguro.id_taller.in_(workshop_ids),
                Seguro.fecha_inicio <= now,
                or_(Seguro.fecha_fin.is_(None), Seguro.fecha_fin >= now),
            )
            .order_by(Seguro.id_taller, Seguro.id_seguro.desc())
        )
    )
    insurance_map: dict[int, list[Seguro]] = {}
    for insurance in insurances:
        insurance_map.setdefault(insurance.id_taller, []).append(insurance)
    return insurance_map


def _resolve_insurance_display(
    *,
    insurance_map: dict[int, list[Seguro]],
    workshop_id: int,
    detected_specialty_id: int,
) -> tuple[bool, bool, str | None]:
    workshop_insurances = insurance_map.get(workshop_id, [])
    if not workshop_insurances:
        return False, False, None

    matching_insurance: Seguro | None = None
    for insurance in workshop_insurances:
        covered_specialties = {
            item.id_especialidad
            for item in insurance.cobertura.especialidades
        }
        if detected_specialty_id in covered_specialties:
            matching_insurance = insurance
            break

    if matching_insurance is not None:
        return True, True, matching_insurance.cobertura.nombre

    return True, False, workshop_insurances[0].cobertura.nombre


def _estimate_workshop_arrival_text(distance_km: Decimal) -> str | None:
    if distance_km <= 0:
        return "Menos de 1 min"
    eta_seconds = int(
        (distance_km / TRACKING_FALLBACK_SPEED_KMH) * Decimal("3600")
    )
    return _format_eta_text(max(eta_seconds, 0))


def _build_diagnosis_summary(incident: Incidente) -> IncidentDiagnosisSummaryResponse:
    triage_details = build_triage_details_from_payload(
        payload=incident.diagnostico_ia_json,
        detected_specialty_name=(
            incident.especialidad_detectada.nombre
            if incident.especialidad_detectada is not None
            else None
        ),
        summary=incident.diagnostico_ia_resumen,
        severity=incident.severidad,
        confidence=incident.confianza_ia,
        requires_manual_review=incident.requiere_revision_manual,
    )
    return IncidentDiagnosisSummaryResponse(
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        incident_latitud=incident.latitud,
        incident_longitud=incident.longitud,
        client_reported_specialty=(
            incident.especialidad_reportada_cliente.nombre
            if incident.especialidad_reportada_cliente is not None
            else None
        ),
        detected_specialty=(
            incident.especialidad_detectada.nombre
            if incident.especialidad_detectada is not None
            else None
        ),
        severity=incident.severidad,
        confidence=incident.confianza_ia,
        ai_summary=triage_details.summary,
        specific_diagnosis=triage_details.specific_diagnosis,
        suggested_service=triage_details.suggested_service,
        customer_recommendation=triage_details.customer_recommendation,
        operator_notes=triage_details.operator_notes,
        visual_evidence_tags=triage_details.visual_evidence_tags,
        audio_summary=triage_details.audio_summary,
        audio_analysis_type=triage_details.audio_analysis_type,
        transcripcion_audio=incident.transcripcion_audio,
        etiquetas_imagen=incident.etiquetas_imagen,
        requires_manual_review=incident.requiere_revision_manual,
        diagnostico_ia_json=incident.diagnostico_ia_json,
        diagnosis_ready=(
            incident.fecha_triaje is not None
            and incident.id_especialidad_detectada is not None
            and incident.severidad is not None
            and not incident.requiere_revision_manual
        ),
    )


def _build_recommended_workshop_response(
    *,
    candidate,
    incident: Incidente,
    insurance_map: dict[int, list[Seguro]],
    latest_requests_by_workshop: dict[int, SolicitudServicio],
    catalog_estimate_map: dict[int, tuple[Decimal, str]],
    is_top_recommendation: bool,
    active_request_id: int | None,
) -> RecommendedWorkshopResponse:
    latest_request = latest_requests_by_workshop.get(candidate.taller.id_taller)
    insurance_exists, insurance_covers_specialty, coverage_name = _resolve_insurance_display(
        insurance_map=insurance_map,
        workshop_id=candidate.taller.id_taller,
        detected_specialty_id=incident.id_especialidad_detectada,
    )
    distance_meters = (candidate.distance_km * Decimal("1000")).quantize(Decimal("0.0001"))
    catalog_estimate = catalog_estimate_map.get(candidate.taller.id_taller)

    return RecommendedWorkshopResponse(
        workshop_id=candidate.taller.id_taller,
        workshop_name=candidate.taller.nombre_comercial,
        latitud=candidate.taller.latitud,
        longitud=candidate.taller.longitud,
        distance_km=candidate.distance_km,
        distance_meters=distance_meters,
        reputation=candidate.taller.reputacion_prom,
        specialty_match=True,
        insurance_exists_with_workshop=insurance_exists,
        insurance_priority_applied=candidate.used_insurance_priority,
        insurance_covering_this_specialty=insurance_covers_specialty,
        coverage_name=coverage_name,
        ranking_score=(
            latest_request.score_total
            if latest_request is not None and latest_request.id_solicitud == active_request_id
            else candidate.score_total
        ),
        estimated_arrival_text=_estimate_workshop_arrival_text(candidate.distance_km),
        estimated_cost=(catalog_estimate[0] if catalog_estimate is not None else None),
        currency=(catalog_estimate[1] if catalog_estimate is not None else None),
        current_matchmaking_status=(
            latest_request.estado if latest_request is not None else None
        ),
        is_top_recommendation=is_top_recommendation,
    )


def _build_catalog_match_text(incident: Incidente) -> str:
    diagnosis_parts: list[str] = []
    if incident.diagnostico_ia_resumen:
        diagnosis_parts.append(incident.diagnostico_ia_resumen)
    if incident.diagnostico_ia_json:
        diagnosis_parts.append(str(incident.diagnostico_ia_json))
    return _normalize_catalog_name(" ".join(diagnosis_parts)) or ""


def _select_catalog_for_estimate(
    *,
    catalog_rows: list[CatalogoServicioTaller],
    incident: Incidente,
) -> CatalogoServicioTaller | None:
    if not catalog_rows:
        return None
    diagnosis_text = _build_catalog_match_text(incident)
    ordered = sorted(
        catalog_rows,
        key=lambda item: (
            0
            if (
                diagnosis_text
                and _normalize_catalog_name(item.nombre) is not None
                and _normalize_catalog_name(item.nombre) in diagnosis_text
            )
            else 1,
            item.precio_base_min,
            item.precio_base_max,
            item.id_catalogo_servicio,
        ),
    )
    return ordered[0]


def _get_workshop_catalog_estimate_map(
    db: Session,
    *,
    workshop_ids: list[int],
    incident: Incidente,
) -> dict[int, tuple[Decimal, str]]:
    if not workshop_ids or incident.id_especialidad_detectada is None:
        return {}
    catalog_rows = list(
        db.scalars(
            select(CatalogoServicioTaller)
            .where(
                CatalogoServicioTaller.id_taller.in_(workshop_ids),
                CatalogoServicioTaller.id_especialidad == incident.id_especialidad_detectada,
                CatalogoServicioTaller.activo.is_(True),
            )
            .order_by(
                CatalogoServicioTaller.id_taller,
                CatalogoServicioTaller.precio_base_min.asc(),
                CatalogoServicioTaller.precio_base_max.asc(),
                CatalogoServicioTaller.id_catalogo_servicio.asc(),
            )
        )
    )
    grouped: dict[int, list[CatalogoServicioTaller]] = {}
    for row in catalog_rows:
        grouped.setdefault(row.id_taller, []).append(row)

    estimate_map: dict[int, tuple[Decimal, str]] = {}
    for workshop_id, items in grouped.items():
        selected = _select_catalog_for_estimate(catalog_rows=items, incident=incident)
        if selected is None:
            continue
        midpoint = ((selected.precio_base_min + selected.precio_base_max) / Decimal("2")).quantize(
            Decimal("0.01")
        )
        estimate_map[workshop_id] = (midpoint, PREQUOTATION_CURRENCY)
    return estimate_map


def _build_client_prequotation_response(
    *,
    service: Servicio,
    payload: dict[str, object] | None,
) -> ServicePrequotationResponse:
    if (
        service.codigo_precotizacion is None
        or service.monto_precotizado_min is None
        or service.monto_precotizado_max is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service prequotation is not available yet.",
        )
    return ServicePrequotationResponse(
        service_id=service.id_servicio,
        incident_id=service.solicitud.incidente.id_incidente,
        prequotation_code=service.codigo_precotizacion,
        prequotation_min=service.monto_precotizado_min,
        prequotation_max=service.monto_precotizado_max,
        prequotation_currency=PREQUOTATION_CURRENCY,
        catalog_service_name=(
            str(payload.get("catalog_service_name"))
            if payload is not None and payload.get("catalog_service_name") is not None
            else None
        ),
        incluye_repuestos_basicos=(
            bool(payload.get("incluye_repuestos_basicos"))
            if payload is not None and payload.get("incluye_repuestos_basicos") is not None
            else None
        ),
        message="Esta precotizacion es referencial antes del diagnostico fisico del operario.",
    )


def _build_client_active_service_summary(
    service: Servicio,
) -> ClientActiveServiceSummaryResponse:
    incident = service.solicitud.incidente
    operario_name = None
    if service.operario is not None and service.operario.persona is not None:
        operario_name = (
            f"{service.operario.persona.nombre} {service.operario.persona.apellido}"
        ).strip()

    return ClientActiveServiceSummaryResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        workshop_name=service.solicitud.taller.nombre_comercial,
        operario_name=operario_name or None,
        detected_specialty=(
            incident.especialidad_detectada.nombre
            if incident.especialidad_detectada is not None
            else None
        ),
        ai_summary=incident.diagnostico_ia_resumen,
        prequotation_code=service.codigo_precotizacion,
        prequotation_min=service.monto_precotizado_min,
        prequotation_max=service.monto_precotizado_max,
        prequotation_currency=(
            PREQUOTATION_CURRENCY
            if service.codigo_precotizacion is not None
            else None
        ),
        created_at=service.created_at,
        assigned_at=service.fecha_asignacion_operario,
    )


def _build_recommendation_context(
    *,
    db: Session,
    incident: Incidente,
    cliente_id: int,
) -> tuple[SolicitudServicio | None, list, dict[int, list[Seguro]], dict[int, SolicitudServicio]]:
    active_request = _get_active_incident_request(incident)
    attempted_workshop_ids = _get_attempted_workshop_ids(
        db,
        incident_id=incident.id_incidente,
    )
    remaining_candidates = _build_ranked_candidates(
        db,
        incident=incident,
        attempted_workshop_ids=attempted_workshop_ids,
        now=utc_now(),
    )

    ordered_candidates: list = []
    if active_request is not None:
        ordered_candidates.append(
            build_ranked_candidate(
                incident_lat=incident.latitud,
                incident_lon=incident.longitud,
                taller=active_request.taller,
                used_insurance_priority=active_request.prioridad_seguro,
            )
        )
    ordered_candidates.extend(remaining_candidates)

    workshop_ids = {candidate.taller.id_taller for candidate in ordered_candidates}
    insurance_map = _get_active_insurance_map(
        db,
        cliente_id=cliente_id,
        workshop_ids=workshop_ids,
    )
    latest_requests_by_workshop = _get_latest_request_by_workshop(incident)
    return active_request, ordered_candidates, insurance_map, latest_requests_by_workshop


def _get_next_incident_attempt_number(incident: Incidente) -> int:
    if not incident.solicitudes:
        return 1
    return max(item.intento_numero for item in incident.solicitudes) + 1


def _create_hire_workshop_notification(
    *,
    db: Session,
    user: Usuario,
    request_row: SolicitudServicio,
    incident: Incidente,
    workshop_name: str,
) -> None:
    db.add(
        Notificacion(
            id_usuario=user.id_usuario,
            id_solicitud=request_row.id_solicitud,
            canal="WEB",
            titulo="Nueva solicitud de auxilio",
            mensaje=(
                f"El incidente {incident.id_incidente} fue contratado para el taller "
                f"{workshop_name} y requiere revision administrativa."
            ),
            payload={
                "incident_id": incident.id_incidente,
                "request_id": request_row.id_solicitud,
                "workshop_id": request_row.id_taller,
                "request_state": request_row.estado,
            },
            estado="PENDIENTE",
        )
    )


def start_navigation(
    *,
    service_id: int,
    payload: NavigationStartRequest,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> NavigationStartResponse:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    incident = _validate_navigation_status_eligible(service)
    _validate_navigation_start_eligible(
        service=service,
        incident=incident,
        current_user=current_user,
        db=db,
    )

    try:
        route = get_route(
            origin_lat=payload.latitud_actual,
            origin_lon=payload.longitud_actual,
            dest_lat=incident.latitud,
            dest_lon=incident.longitud,
        )
    except RouteProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Route provider could not build a navigation route.",
        ) from exc

    now = utc_now()
    location = _persist_location_point(
        db=db,
        service=service,
        latitud=payload.latitud_actual,
        longitud=payload.longitud_actual,
        accuracy_meters=payload.accuracy_meters,
        speed_mps=payload.speed_mps,
        device_timestamp=now,
        route_data={
            "origin_lat": payload.latitud_actual,
            "origin_lon": payload.longitud_actual,
            "dest_lat": incident.latitud,
            "dest_lon": incident.longitud,
            "distance_meters": route.distance_meters,
            "duration_seconds": route.duration_seconds,
            "geometry": route.geometry,
        },
    )

    message = "Navigation route created successfully."
    if service.estado == "ASIGNADO":
        service.estado = "EN_CAMINO"
        db.add(
            _create_navigation_bitacora(
                current_user=current_user,
                service=service,
                incident=incident,
                accion="NAVEGACION_INICIADA",
                descripcion="El operario inicio la navegacion hacia el incidente.",
                datos_nuevos={
                    "service_state": service.estado,
                    "origin_latitud": str(payload.latitud_actual),
                    "origin_longitud": str(payload.longitud_actual),
                    "route_distance_meters": str(route.distance_meters),
                    "route_duration_seconds": str(route.duration_seconds),
                    "provider": route.provider,
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )
        client_user = _get_client_user(db, cliente_id=incident.id_cliente)
        _create_typed_notification(
            db=db,
            user=client_user,
            notification_type=NOTIFICATION_TYPE_OPERARIO_EN_CAMINO,
            title="Operario en camino",
            message="El operario va en camino hacia tu ubicacion.",
            service=service,
            incident_id=incident.id_incidente,
        )
        message = "Navigation started successfully."

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Navigation start could not be persisted.",
        ) from exc

    if message == "Navigation started successfully.":
        client_user = _get_client_user(db, cliente_id=incident.id_cliente)
        _auto_dispatch_notifications(target_user=client_user, db=db)

    return NavigationStartResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        destination_latitud=incident.latitud,
        destination_longitud=incident.longitud,
        origin_latitud=payload.latitud_actual,
        origin_longitud=payload.longitud_actual,
        route_distance_meters=route.distance_meters,
        route_duration_seconds=route.duration_seconds,
        geometry=route.geometry,
        steps=[
            RouteStepSummary(
                distance_meters=step.distance_meters,
                duration_seconds=step.duration_seconds,
                name=step.name,
                maneuver_type=step.maneuver_type,
                maneuver_modifier=step.maneuver_modifier,
                instruction=step.instruction,
            )
            for step in route.steps
        ],
        arrival_threshold_meters=settings.navigation_arrival_threshold_meters,
        location_point_id=location.id_ubicacion,
        message=message,
    )


def update_service_location(
    *,
    service_id: int,
    payload: ServiceLocationUpdateRequest,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> ServiceLocationUpdateResponse:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    incident = _validate_navigation_status_eligible(service)
    if service.estado == "ASIGNADO":
        _validate_navigation_start_eligible(
            service=service,
            incident=incident,
            current_user=current_user,
            db=db,
        )

    location = _persist_location_point(
        db=db,
        service=service,
        latitud=payload.latitud,
        longitud=payload.longitud,
        accuracy_meters=payload.accuracy_meters,
        speed_mps=payload.speed_mps,
        device_timestamp=payload.device_timestamp,
    )

    if service.estado == "ASIGNADO":
        service.estado = "EN_CAMINO"
        if not db.scalar(
            select(
                exists().where(
                    Bitacora.id_servicio == service.id_servicio,
                    Bitacora.accion == "NAVEGACION_INICIADA",
                )
            )
        ):
            db.add(
                _create_navigation_bitacora(
                    current_user=current_user,
                    service=service,
                    incident=incident,
                    accion="NAVEGACION_INICIADA",
                    descripcion="El operario inicio desplazamiento con su primera ubicacion valida.",
                    datos_nuevos={
                        "service_state": service.estado,
                        "latitud": str(payload.latitud),
                        "longitud": str(payload.longitud),
                    },
                    ip_origen=ip_origen,
                    user_agent=user_agent,
                )
            )

    current_distance_meters = _distance_to_incident_meters(
        incident=incident,
        latitud=payload.latitud,
        longitud=payload.longitud,
    )
    has_arrived = _mark_arrival_if_needed(
        db=db,
        service=service,
        incident=incident,
        current_user=current_user,
        current_distance_meters=current_distance_meters,
        ip_origen=ip_origen,
        user_agent=user_agent,
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service location update could not be persisted.",
        ) from exc

    return ServiceLocationUpdateResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        current_distance_meters=current_distance_meters,
        arrival_threshold_meters=settings.navigation_arrival_threshold_meters,
        has_arrived=has_arrived,
        location_point_id=location.id_ubicacion,
        message=(
            "Operario has arrived on site."
            if has_arrived
            else "Service location updated successfully."
        ),
    )


def get_navigation_status(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> NavigationStatusResponse:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    incident = _validate_navigation_status_eligible(service)
    last_location = _get_last_location(db, service_id=service.id_servicio)
    profile_acknowledged = bool(
        db.scalar(
            select(
                exists().where(
                    Bitacora.id_servicio == service.id_servicio,
                    Bitacora.accion == "PERFIL_FALLA_ESTRUCTURADO_ACK",
                    Bitacora.id_usuario == current_user.id_usuario,
                )
            )
        )
    )
    current_distance_meters = None
    if last_location is not None:
        current_distance_meters = _distance_to_incident_meters(
            incident=incident,
            latitud=last_location.latitud,
            longitud=last_location.longitud,
        )
    has_arrived = service.estado == "EN_SITIO" or _arrival_already_recorded(
        db,
        service_id=service.id_servicio,
    )

    route_location = _get_route_data(db, service_id=service.id_servicio)

    return NavigationStatusResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        destination_latitud=incident.latitud,
        destination_longitud=incident.longitud,
        last_known_latitud=last_location.latitud if last_location else None,
        last_known_longitud=last_location.longitud if last_location else None,
        last_known_at=last_location.fecha_hora if last_location else None,
        current_distance_meters=current_distance_meters,
        profile_acknowledged=profile_acknowledged,
        has_arrived=has_arrived,
        arrival_threshold_meters=settings.navigation_arrival_threshold_meters,
        route_distance_meters=(
            route_location.ruta_distancia_metros if route_location is not None else None
        ),
        route_duration_seconds=(
            route_location.ruta_duracion_segundos if route_location is not None else None
        ),
        route_geometry=(
            route_location.ruta_geometria if route_location is not None else None
        ),
        message="Navigation status loaded successfully.",
    )


def get_client_tracking_status(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> TrackingStatusResponse:
    service = _get_client_owned_service(
        db,
        service_id=service_id,
        cliente_id=current_user.id_persona,
    )
    incident = _validate_tracking_eligible(service)
    last_location = _get_last_location(db, service_id=service.id_servicio)
    location_stale = _is_location_stale(last_location)
    current_distance_meters = None
    eta_seconds = None
    eta_text = None
    has_live_location = last_location is not None and not location_stale

    if last_location is not None:
        current_distance_meters = _distance_to_incident_meters(
            incident=incident,
            latitud=last_location.latitud,
            longitud=last_location.longitud,
        )
        eta_seconds = _estimate_eta_seconds(
            current_distance_meters=current_distance_meters,
            location=last_location,
        )
        eta_text = _format_eta_text(eta_seconds)

    if last_location is None:
        tracking_message = "No operario location is available yet."
    elif location_stale:
        tracking_message = "Operario location is stale."
    else:
        tracking_message = "Operario tracking is available."

    return TrackingStatusResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        incident_latitud=incident.latitud,
        incident_longitud=incident.longitud,
        last_operario_latitud=last_location.latitud if last_location is not None else None,
        last_operario_longitud=last_location.longitud if last_location is not None else None,
        last_location_at=last_location.fecha_hora if last_location is not None else None,
        has_live_location=has_live_location,
        location_stale=location_stale,
        current_distance_meters=current_distance_meters,
        eta_seconds=eta_seconds,
        eta_text=eta_text,
        tracking_message=tracking_message,
    )


def get_client_tracking_history(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> list[TrackingHistoryPointResponse]:
    service = _get_client_owned_service(
        db,
        service_id=service_id,
        cliente_id=current_user.id_persona,
    )
    _validate_tracking_eligible(service)
    points = _get_recent_tracking_points(db, service_id=service.id_servicio)
    return [
        TrackingHistoryPointResponse(
            latitud=item.latitud,
            longitud=item.longitud,
            fecha_hora=item.fecha_hora,
        )
        for item in points
    ]


def get_incident_recommendations(
    *,
    incident_id: int,
    current_user: Usuario,
    db: Session,
) -> IncidentRecommendationsResponse:
    incident = _get_client_owned_incident(
        db,
        incident_id=incident_id,
        cliente_id=current_user.id_persona,
    )
    _validate_recommendations_diagnosis_ready(incident)

    if not incident.solicitudes and not _has_matchmaking_history(
        db,
        incident_id=incident.id_incidente,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident recommendations are not ready yet.",
        )

    active_request, ordered_candidates, insurance_map, latest_requests_by_workshop = (
        _build_recommendation_context(
            db=db,
            incident=incident,
            cliente_id=current_user.id_persona,
        )
    )
    active_request_id = active_request.id_solicitud if active_request is not None else None
    catalog_estimate_map = _get_workshop_catalog_estimate_map(
        db=db,
        workshop_ids=[candidate.taller.id_taller for candidate in ordered_candidates],
        incident=incident,
    )

    recommendations = [
        _build_recommended_workshop_response(
            candidate=candidate,
            incident=incident,
            insurance_map=insurance_map,
            latest_requests_by_workshop=latest_requests_by_workshop,
            catalog_estimate_map=catalog_estimate_map,
            is_top_recommendation=index == 0,
            active_request_id=active_request_id,
        )
        for index, candidate in enumerate(ordered_candidates)
    ]

    has_recommendations = bool(recommendations)
    return IncidentRecommendationsResponse(
        diagnosis=_build_diagnosis_summary(incident),
        recommended_workshops=recommendations,
        has_recommendations=has_recommendations,
        top_recommendation_workshop_id=(
            recommendations[0].workshop_id if has_recommendations else None
        ),
        message=(
            "Recommendations loaded successfully."
            if has_recommendations
            else "Diagnosis is ready, but no compatible workshops are currently available."
        ),
    )


def hire_incident_workshop(
    *,
    incident_id: int,
    payload: HireWorkshopRequest,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> HireWorkshopResponse:
    incident = _get_client_owned_incident(
        db,
        incident_id=incident_id,
        cliente_id=current_user.id_persona,
    )
    _validate_recommendations_diagnosis_ready(incident)

    if not incident.solicitudes and not _has_matchmaking_history(
        db,
        incident_id=incident.id_incidente,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident recommendations are not ready yet.",
        )

    active_request, ordered_candidates, insurance_map, _ = _build_recommendation_context(
        db=db,
        incident=incident,
        cliente_id=current_user.id_persona,
    )
    candidate_map = {candidate.taller.id_taller: candidate for candidate in ordered_candidates}
    selected_candidate = candidate_map.get(payload.workshop_id)
    if selected_candidate is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected workshop is not a valid recommendation for this incident.",
        )

    if active_request is not None:
        if active_request.id_taller == payload.workshop_id:
            return HireWorkshopResponse(
                incident_id=incident.id_incidente,
                request_id=active_request.id_solicitud,
                workshop_id=active_request.id_taller,
                workshop_name=active_request.taller.nombre_comercial,
                request_state=active_request.estado,
                message="An active hiring request already exists for this workshop.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident already has an active workshop request in the current cycle.",
        )

    now = utc_now()
    insurance_exists, insurance_covers_specialty, coverage_name = _resolve_insurance_display(
        insurance_map=insurance_map,
        workshop_id=selected_candidate.taller.id_taller,
        detected_specialty_id=incident.id_especialidad_detectada,
    )
    request_row = SolicitudServicio(
        id_incidente=incident.id_incidente,
        id_taller=selected_candidate.taller.id_taller,
        fecha_envio=now,
        fecha_expiracion=now + timedelta(seconds=settings.matchmaking_request_ttl_seconds),
        estado="PENDIENTE",
        prioridad_seguro=selected_candidate.used_insurance_priority,
        score_proximidad=selected_candidate.score_proximidad,
        score_reputacion=selected_candidate.score_reputacion,
        score_total=selected_candidate.score_total,
        ranking_posicion=(
            next(
                (
                    index
                    for index, item in enumerate(ordered_candidates, start=1)
                    if item.taller.id_taller == selected_candidate.taller.id_taller
                ),
                1,
            )
        ),
        intento_numero=_get_next_incident_attempt_number(incident),
        es_actual=True,
    )
    incident.estado = "EN_MATCHMAKING"
    db.add(request_row)
    db.flush()

    db.add(
        Bitacora(
            accion="SOLICITUD_AUXILIO_CREADA",
            tipo_evento="CONTRATACION",
            descripcion="El cliente creo una solicitud formal de auxilio para un taller recomendado.",
            entidad_principal="SOLICITUD",
            id_entidad_principal=request_row.id_solicitud,
            datos_nuevos={
                "incident_id": incident.id_incidente,
                "request_id": request_row.id_solicitud,
                "workshop_id": selected_candidate.taller.id_taller,
                "client_id": current_user.id_persona,
                "detected_specialty_id": incident.id_especialidad_detectada,
                "insurance_exists_with_workshop": insurance_exists,
                "insurance_covering_this_specialty": insurance_covers_specialty,
                "coverage_name": coverage_name,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
            hash_evento="",
            id_usuario=current_user.id_usuario,
            id_incidente=incident.id_incidente,
            id_solicitud=request_row.id_solicitud,
        )
    )

    workshop_admin_users = _get_workshop_admin_users(
        db,
        workshop_id=selected_candidate.taller.id_taller,
    )
    for admin_user in workshop_admin_users:
        _create_hire_workshop_notification(
            db=db,
            user=admin_user,
            request_row=request_row,
            incident=incident,
            workshop_name=selected_candidate.taller.nombre_comercial,
        )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workshop hiring request could not be created.",
        ) from exc

    for admin_user in workshop_admin_users:
        try:
            _dispatch_pending_notifications_for_user(
                target_user=admin_user,
                db=db,
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        except HTTPException:
            db.rollback()

    return HireWorkshopResponse(
        incident_id=incident.id_incidente,
        request_id=request_row.id_solicitud,
        workshop_id=selected_candidate.taller.id_taller,
        workshop_name=selected_candidate.taller.nombre_comercial,
        request_state=request_row.estado,
        message="Workshop hiring request created successfully.",
    )


def get_client_service_prequotation(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> ServicePrequotationResponse:
    service = _get_client_owned_service(
        db,
        service_id=service_id,
        cliente_id=current_user.id_persona,
    )
    payload = _get_latest_service_prequotation_payload(
        db,
        service_id=service.id_servicio,
    )
    return _build_client_prequotation_response(
        service=service,
        payload=payload,
    )


def list_client_active_services(
    *,
    current_user: Usuario,
    db: Session,
) -> list[ClientActiveServiceSummaryResponse]:
    services = list(
        db.scalars(
            _build_service_query()
            .join(
                SolicitudServicio,
                SolicitudServicio.id_solicitud == Servicio.id_solicitud,
            )
            .join(
                Incidente,
                Incidente.id_incidente == SolicitudServicio.id_incidente,
            )
            .where(
                Incidente.id_cliente == current_user.id_persona,
                Servicio.estado.in_(tuple(CLIENT_ACTIVE_SERVICE_STATES)),
            )
            .order_by(
                Servicio.created_at.desc(),
                Servicio.id_servicio.desc(),
            )
        )
    )
    return [_build_client_active_service_summary(item) for item in services]


def register_notification_device(
    *,
    payload: DeviceRegistrationRequest,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> DeviceRegistrationResponse:
    now = utc_now()
    device = _get_user_device_by_token(db, token_push=payload.device_token)

    if device is None:
        device = DispositivoUsuario(
            id_usuario=current_user.id_usuario,
            plataforma=payload.platform,
            token_push=payload.device_token,
            activo=payload.notifications_enabled,
            ultimo_registro=now,
        )
        db.add(device)
        action = "registered"
    else:
        device.id_usuario = current_user.id_usuario
        device.plataforma = payload.platform
        device.activo = payload.notifications_enabled
        device.ultimo_registro = now
        action = "updated"

    db.add(
        _create_notification_bitacora(
            current_user=current_user,
            accion="DISPOSITIVO_NOTIFICACION_REGISTRADO",
            descripcion="El usuario registro o reactivo un dispositivo para notificaciones push.",
            entidad_principal="USUARIO",
            id_entidad_principal=current_user.id_usuario,
            datos_nuevos={
                "action": action,
                "platform": payload.platform,
                "notifications_enabled": payload.notifications_enabled,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Notification device could not be registered.",
        ) from exc

    db.refresh(device)
    return DeviceRegistrationResponse(
        device_id=device.id_dispositivo,
        user_id=device.id_usuario,
        device_token=device.token_push,
        platform=device.plataforma,
        active=device.activo,
        registered_at=device.ultimo_registro,
        message="Notification device registered successfully.",
    )


def unregister_notification_device(
    *,
    payload: DeviceUnregisterRequest,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> DeviceRegistrationResponse:
    device = db.scalar(
        select(DispositivoUsuario).where(
            DispositivoUsuario.token_push == payload.device_token,
            DispositivoUsuario.id_usuario == current_user.id_usuario,
        )
    )
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification device not found.",
        )

    device.activo = False
    device.ultimo_registro = utc_now()
    db.add(
        _create_notification_bitacora(
            current_user=current_user,
            accion="DISPOSITIVO_NOTIFICACION_DESACTIVADO",
            descripcion="El usuario desactivo un dispositivo de notificaciones push.",
            entidad_principal="USUARIO",
            id_entidad_principal=current_user.id_usuario,
            datos_nuevos={
                "device_id": device.id_dispositivo,
                "platform": device.plataforma,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Notification device could not be unregistered.",
        ) from exc

    return DeviceRegistrationResponse(
        device_id=device.id_dispositivo,
        user_id=device.id_usuario,
        device_token=device.token_push,
        platform=device.plataforma,
        active=device.activo,
        registered_at=device.ultimo_registro,
        message="Notification device unregistered successfully.",
    )


def get_my_notifications(
    *,
    current_user: Usuario,
    db: Session,
    only_unread: bool,
    limit: int,
) -> list[NotificationInboxItem]:
    normalized_limit = max(1, min(limit, NOTIFICATION_INBOX_LIMIT))
    query = (
        select(Notificacion)
        .where(Notificacion.id_usuario == current_user.id_usuario)
        .order_by(
            Notificacion.fecha_creacion.desc(),
            Notificacion.id_notificacion.desc(),
        )
        .limit(normalized_limit)
    )
    if only_unread:
        query = query.where(Notificacion.estado != "LEIDA")

    notifications = list(db.scalars(query))
    return [_serialize_notification_item(item) for item in notifications]


def mark_notification_as_read(
    *,
    notification_id: int,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> NotificationReadResponse:
    notification = _get_user_notification(
        db,
        notification_id=notification_id,
        user_id=current_user.id_usuario,
    )
    if notification.estado == "LEIDA":
        return NotificationReadResponse(
            notification_id=notification.id_notificacion,
            status=notification.estado,
            read_at=notification.fecha_lectura,
            message="Notification was already marked as read.",
        )

    read_at = utc_now()
    notification.estado = "LEIDA"
    notification.fecha_lectura = read_at
    if notification.fecha_envio is None:
        notification.fecha_envio = read_at

    db.add(
        _create_notification_bitacora(
            current_user=current_user,
            accion="NOTIFICACION_MARCADA_LEIDA",
            descripcion="El usuario marco una notificacion como leida.",
            entidad_principal="NOTIFICACION",
            id_entidad_principal=notification.id_notificacion,
            datos_nuevos={
                "notification_id": notification.id_notificacion,
                "status": notification.estado,
            },
            notification=notification,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Notification could not be marked as read.",
        ) from exc

    return NotificationReadResponse(
        notification_id=notification.id_notificacion,
        status=notification.estado,
        read_at=notification.fecha_lectura,
        message="Notification marked as read successfully.",
    )


def get_my_unread_notification_count(
    *,
    current_user: Usuario,
    db: Session,
) -> UnreadCountResponse:
    unread_count = db.scalar(
        select(func.count(Notificacion.id_notificacion)).where(
            Notificacion.id_usuario == current_user.id_usuario,
            Notificacion.estado != "LEIDA",
        )
    )
    return UnreadCountResponse(unread_count=int(unread_count or 0))


def mark_all_notifications_as_read(
    *,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> MarkAllReadResponse:
    now = utc_now()
    marked = db.execute(
        select(Notificacion).where(
            Notificacion.id_usuario == current_user.id_usuario,
            Notificacion.estado != "LEIDA",
        )
    ).scalars().all()

    for notification in marked:
        notification.estado = "LEIDA"
        notification.fecha_lectura = now
        if notification.fecha_envio is None:
            notification.fecha_envio = now
        db.add(notification)

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Notifications could not be marked as read.",
        ) from exc

    return MarkAllReadResponse(
        marked_count=len(marked),
        message="All notifications marked as read successfully.",
    )


def _dispatch_pending_notifications_for_user(
    *,
    target_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> DispatchPendingResponse:
    devices = _get_active_user_devices(db, user_id=target_user.id_usuario)
    notifications = _get_sendable_notifications(db, user_id=target_user.id_usuario)

    if not notifications:
        return DispatchPendingResponse(
            provider=settings.push_provider,
            active_device_count=len(devices),
            total_pending=0,
            dispatched_count=0,
            failed_count=0,
            skipped_count=0,
            message="No pending notifications were available for dispatch.",
        )

    if not devices:
        return DispatchPendingResponse(
            provider=settings.push_provider,
            active_device_count=0,
            total_pending=len(notifications),
            dispatched_count=0,
            failed_count=0,
            skipped_count=0,
            message="No active devices are registered. Notifications remain in the inbox.",
        )

    dispatched_count = 0
    failed_count = 0
    skipped_count = 0
    device_tokens = [device.token_push for device in devices]

    for notification in notifications:
        if notification.estado not in NOTIFICATION_SENDABLE_STATES:
            skipped_count += 1
            continue
        if not device_tokens:
            skipped_count += 1
            continue

        push_payload: dict[str, object] = {
            "notification_id": notification.id_notificacion,
        }
        if isinstance(notification.payload, dict):
            push_payload.update(notification.payload)
        elif notification.payload is not None:
            push_payload["payload"] = notification.payload
        if notification.id_servicio is not None:
            push_payload["service_id"] = notification.id_servicio
        if notification.id_solicitud is not None:
            push_payload["request_id"] = notification.id_solicitud

        try:
            result = send_push_notification(
                device_tokens=device_tokens,
                title=notification.titulo,
                message=notification.mensaje,
                payload=push_payload,
            )
        except PushProviderError as exc:
            failed_count += 1
            notification.estado = "FALLIDA"
            notification.proveedor = settings.push_provider
            db.add(
                _create_notification_bitacora(
                    current_user=target_user,
                    accion="NOTIFICACION_PUSH_FALLIDA",
                    descripcion="El proveedor de push no pudo procesar la notificacion.",
                    entidad_principal="NOTIFICACION",
                    id_entidad_principal=notification.id_notificacion,
                    datos_nuevos={
                        "notification_id": notification.id_notificacion,
                        "provider": settings.push_provider,
                        "device_count": len(devices),
                        "result": "provider_error",
                        "detail": str(exc),
                    },
                    notification=notification,
                    ip_origen=ip_origen,
                    user_agent=user_agent,
                )
            )
            continue

        deactivated_count = _deactivate_invalid_devices(
            db=db,
            current_user=target_user,
            devices=devices,
            invalid_tokens=result.invalid_tokens,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
        if deactivated_count:
            devices = [device for device in devices if device.activo]
            device_tokens = [device.token_push for device in devices]

        if result.success:
            dispatched_count += 1
            notification.estado = "ENVIADA"
            notification.fecha_envio = notification.fecha_envio or utc_now()
            notification.proveedor = result.provider
            db.add(
                _create_notification_bitacora(
                    current_user=target_user,
                    accion="NOTIFICACION_PUSH_ENVIADA",
                    descripcion="La notificacion se despacho por push al menos a un dispositivo.",
                    entidad_principal="NOTIFICACION",
                    id_entidad_principal=notification.id_notificacion,
                    datos_nuevos={
                        "notification_id": notification.id_notificacion,
                        "provider": result.provider,
                        "device_count": len(devices),
                        "sent_count": result.sent_count,
                        "failed_count": result.failed_count,
                        "deactivated_devices": deactivated_count,
                        "result": "sent",
                    },
                    notification=notification,
                    ip_origen=ip_origen,
                    user_agent=user_agent,
                )
            )
            continue

        failed_count += 1
        notification.estado = "FALLIDA"
        notification.proveedor = result.provider
        db.add(
            _create_notification_bitacora(
                current_user=target_user,
                accion="NOTIFICACION_PUSH_FALLIDA",
                descripcion="Ningun dispositivo acepto la notificacion push.",
                entidad_principal="NOTIFICACION",
                id_entidad_principal=notification.id_notificacion,
                datos_nuevos={
                    "notification_id": notification.id_notificacion,
                    "provider": result.provider,
                    "device_count": len(devices),
                    "sent_count": result.sent_count,
                    "failed_count": result.failed_count,
                    "deactivated_devices": deactivated_count,
                    "result": "failed",
                    "detail": result.detail,
                },
                notification=notification,
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pending notifications could not be dispatched.",
        ) from exc

    if dispatched_count:
        message = "Pending notifications were dispatched successfully."
    elif failed_count:
        message = "Pending notifications could not be delivered to any active device."
    else:
        message = "No notification required dispatch changes."

    return DispatchPendingResponse(
        provider=settings.push_provider,
        active_device_count=len([device for device in devices if device.activo]),
        total_pending=len(notifications),
        dispatched_count=dispatched_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        message=message,
    )


def dispatch_pending_notifications(
    *,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> DispatchPendingResponse:
    return _dispatch_pending_notifications_for_user(
        target_user=current_user,
        db=db,
        ip_origen=ip_origen,
        user_agent=user_agent,
    )


def get_finalization_status(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> FinalizationStatusResponse:
    if current_user.tipo_usuario == "OPERARIO":
        service = _get_assigned_service(
            db,
            service_id=service_id,
            operario_id=current_user.id_persona,
        )
    elif current_user.tipo_usuario == "CLIENTE":
        service = _get_client_owned_service(
            db,
            service_id=service_id,
            cliente_id=current_user.id_persona,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for CLIENTE or OPERARIO.",
        )

    response = _build_finalization_status(service)
    response.timeline = _get_finalization_timeline(db, service_id=service.id_servicio)
    return response


def get_service_progress_snapshot(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> ServiceProgressSnapshotResponse:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    incident = _validate_progress_eligible(service)
    return ServiceProgressSnapshotResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        detected_specialty=(
            incident.especialidad_detectada.nombre
            if incident.especialidad_detectada is not None
            else None
        ),
        ai_summary=incident.diagnostico_ia_resumen,
        profile_acknowledged=_is_profile_acknowledged(
            db=db,
            service_id=service.id_servicio,
            user_id=current_user.id_usuario,
        ),
        arrival_recorded=_arrival_already_recorded(db, service_id=service.id_servicio),
        allowed_next_states=_get_allowed_next_states(service.estado),
        timeline=_get_progress_timeline(db, service_id=service.id_servicio, limit=10),
    )


def get_service_progress_history(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> list[ServiceProgressHistoryItem]:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    _validate_progress_eligible(service)
    return _get_progress_timeline(db, service_id=service.id_servicio, limit=None)


def update_service_progress(
    *,
    service_id: int,
    payload: ServiceProgressUpdateRequest,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> ServiceProgressUpdateResponse:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    incident = _validate_progress_eligible(service)

    previous_state = service.estado
    requested_state = payload.new_state.strip().upper()
    allowed_next_states = PROGRESS_TRANSITIONS.get(previous_state, set())

    if requested_state == previous_state:
        return ServiceProgressUpdateResponse(
            service_id=service.id_servicio,
            previous_state=previous_state,
            new_state=previous_state,
            incident_id=incident.id_incidente,
            incident_state=incident.estado,
            changed_at=utc_now(),
            message="Service is already in the requested state.",
        )

    if requested_state not in allowed_next_states:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requested service state transition is not allowed.",
        )

    changed_at = utc_now()
    service.estado = requested_state
    db.add(
        _create_navigation_bitacora(
            current_user=current_user,
            service=service,
            incident=incident,
            accion="SERVICIO_ESTADO_ACTUALIZADO",
            descripcion="El operario actualizo el estado operativo del servicio en campo.",
            datos_nuevos={
                "previous_state": previous_state,
                "new_state": requested_state,
                "observacion": payload.observacion,
                "changed_at": changed_at.isoformat(),
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    from .notification_types import (
        NOTIFICATION_TYPE_GENERAL,
        NOTIFICATION_TYPE_SERVICIO_INICIADO,
    )

    client_user = _get_client_user(db, cliente_id=incident.id_cliente)
    client_notification_type = (
        NOTIFICATION_TYPE_SERVICIO_INICIADO
        if previous_state == "EN_SITIO" and requested_state in ("EN_DIAGNOSTICO_FISICO", "EN_REPARACION")
        else NOTIFICATION_TYPE_GENERAL
    )
    _create_typed_notification(
        db=db,
        user=client_user,
        notification_type=client_notification_type,
        title="Actualizacion del servicio",
        message=f"Tu servicio ahora esta en estado {requested_state}.",
        service=service,
        incident_id=incident.id_incidente,
        extra_payload={"new_state": requested_state},
    )
    for admin_user in _get_workshop_admin_users(
        db,
        workshop_id=service.solicitud.id_taller,
    ):
        _create_typed_notification(
            db=db,
            user=admin_user,
            notification_type=NOTIFICATION_TYPE_GENERAL,
            title="Progreso del servicio actualizado",
            message=(
                f"El operario actualizo el servicio {service.id_servicio} "
                f"a {requested_state}."
            ),
            service=service,
            incident_id=incident.id_incidente,
            extra_payload={"new_state": requested_state},
        )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service progress update could not be persisted.",
        ) from exc

    _auto_dispatch_notifications(target_user=client_user, db=db)

    return ServiceProgressUpdateResponse(
        service_id=service.id_servicio,
        previous_state=previous_state,
        new_state=requested_state,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        changed_at=changed_at,
        message="Service progress updated successfully.",
    )


def request_service_finalization(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> FinalizationRequestResponse:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    incident = _validate_finalization_request_eligible(service)
    requested_at = utc_now()
    final_evidence_count = _get_final_evidence_count(service)

    if _has_pending_finalization_request(db, service=service):
        return FinalizationRequestResponse(
            service_id=service.id_servicio,
            service_state=service.estado,
            incident_id=incident.id_incidente,
            incident_state=incident.estado,
            client_decision_pending=True,
            final_evidence_count=final_evidence_count,
            requested_at=requested_at,
            message="Finalization had already been requested for this service.",
        )

    db.add(
        _create_navigation_bitacora(
            current_user=current_user,
            service=service,
            incident=incident,
            accion="FINALIZACION_SOLICITADA",
            descripcion="El operario solicito la validacion final del servicio al cliente.",
            datos_nuevos={
                "previous_state": service.estado,
                "new_state": service.estado,
                "changed_at": requested_at.isoformat(),
                "final_evidence_count": final_evidence_count,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    client_user = _get_client_user(db, cliente_id=incident.id_cliente)
    _create_service_notification(
        db=db,
        user=client_user,
        service=service,
        title="Servicio listo para validacion",
        message="El operario solicito tu validacion final del servicio realizado.",
        payload={
            "service_id": service.id_servicio,
            "incident_id": incident.id_incidente,
            "service_state": service.estado,
            "final_evidence_count": final_evidence_count,
        },
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Finalization request could not be persisted.",
        ) from exc

    return FinalizationRequestResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        client_decision_pending=True,
        final_evidence_count=final_evidence_count,
        requested_at=requested_at,
        message="Finalization requested successfully.",
    )


def decide_service_finalization(
    *,
    service_id: int,
    payload: FinalizationDecisionRequest,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> FinalizationDecisionResponse:
    service = _get_client_owned_service(
        db,
        service_id=service_id,
        cliente_id=current_user.id_persona,
    )
    incident = service.solicitud.incidente
    previous_state = service.estado

    if payload.decision == "CONFIRMAR" and service.estado == FINALIZATION_CONFIRMED_STATE:
        return FinalizationDecisionResponse(
            service_id=service.id_servicio,
            previous_state=service.estado,
            new_state=service.estado,
            incident_id=incident.id_incidente,
            incident_state=incident.estado,
            confirmed_at=service.fecha_confirmacion_cliente,
            duration_seconds=_compute_service_duration_seconds(service),
            final_evidence_count=_get_final_evidence_count(service),
            message="Service finalization was already confirmed.",
        )

    incident = _validate_finalization_decision_eligible(service)
    changed_at = utc_now()
    final_evidence_count = _get_final_evidence_count(service)
    operario_user = _get_operario_user(db, operario_id=service.id_persona_operario)
    admin_users = _get_workshop_admin_users(db, workshop_id=service.solicitud.id_taller)

    if payload.decision == "CONFIRMAR":
        operario = service.operario
        if operario is None and service.id_persona_operario is not None:
            operario = db.scalar(
                select(Operario).where(Operario.id_persona == service.id_persona_operario)
            )
        operario_previous_status = operario.estado_disponibilidad if operario is not None else None

        service.estado = FINALIZATION_CONFIRMED_STATE
        service.confirmacion_cliente = True
        service.fecha_confirmacion_cliente = changed_at
        service.fecha_fin = changed_at
        incident.estado = "FINALIZADO"
        if operario is not None:
            operario.estado_disponibilidad = "DISPONIBLE"
        duration_seconds = _compute_service_duration_seconds(service)

        db.add(
            _create_navigation_bitacora(
                current_user=current_user,
                service=service,
                incident=incident,
                accion="FINALIZACION_CONFIRMADA_CLIENTE",
                descripcion="El cliente confirmo la resolucion del servicio.",
                datos_nuevos={
                    "previous_state": previous_state,
                    "new_state": service.estado,
                    "changed_at": changed_at.isoformat(),
                    "duration_seconds": duration_seconds,
                    "final_evidence_count": final_evidence_count,
                    "operario_previous_status": operario_previous_status,
                    "operario_new_status": operario.estado_disponibilidad if operario is not None else None,
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )

        _create_service_notification(
            db=db,
            user=operario_user,
            service=service,
            title="Servicio confirmado por el cliente",
            message="El cliente confirmo la resolucion del servicio. El caso quedo listo para pago.",
            payload={
                "service_id": service.id_servicio,
                "incident_id": incident.id_incidente,
                "service_state": service.estado,
                "duration_seconds": duration_seconds,
            },
        )
        for admin_user in admin_users:
            _create_service_notification(
                db=db,
                user=admin_user,
                service=service,
                title="Servicio finalizado pendiente de pago",
                message=(
                    f"El cliente confirmo el servicio {service.id_servicio}. "
                    "El caso quedo listo para la etapa de pago."
                ),
                payload={
                    "service_id": service.id_servicio,
                    "incident_id": incident.id_incidente,
                    "service_state": service.estado,
                    "duration_seconds": duration_seconds,
                },
            )

        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Finalization confirmation could not be persisted.",
            ) from exc

        return FinalizationDecisionResponse(
            service_id=service.id_servicio,
            previous_state=previous_state,
            new_state=service.estado,
            incident_id=incident.id_incidente,
            incident_state=incident.estado,
            confirmed_at=service.fecha_confirmacion_cliente,
            duration_seconds=duration_seconds,
            final_evidence_count=final_evidence_count,
            message="Service finalization confirmed successfully.",
        )

    service.estado = FINALIZATION_REWORK_STATE
    service.confirmacion_cliente = False
    service.fecha_confirmacion_cliente = changed_at
    service.observaciones_cierre = payload.motivo
    incident.estado = "EN_PROCESO"

    db.add(
        _create_navigation_bitacora(
            current_user=current_user,
            service=service,
            incident=incident,
            accion="FINALIZACION_RECHAZADA_CLIENTE",
            descripcion="El cliente rechazo la finalizacion del servicio y solicito retrabajo.",
            datos_nuevos={
                "previous_state": previous_state,
                "new_state": service.estado,
                "motivo": payload.motivo,
                "changed_at": changed_at.isoformat(),
                "final_evidence_count": final_evidence_count,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    _create_service_notification(
        db=db,
        user=operario_user,
        service=service,
        title="Finalizacion rechazada por el cliente",
        message="El cliente rechazo la finalizacion del servicio y se requiere retrabajo.",
        payload={
            "service_id": service.id_servicio,
            "incident_id": incident.id_incidente,
            "service_state": service.estado,
            "motivo": payload.motivo,
        },
    )
    for admin_user in admin_users:
        _create_service_notification(
            db=db,
            user=admin_user,
            service=service,
            title="Cliente rechazo finalizacion",
            message=(
                f"El cliente rechazo la finalizacion del servicio {service.id_servicio}. "
                "El caso vuelve a reparacion."
            ),
            payload={
                "service_id": service.id_servicio,
                "incident_id": incident.id_incidente,
                "service_state": service.estado,
                "motivo": payload.motivo,
            },
        )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Finalization rejection could not be persisted.",
        ) from exc

    return FinalizationDecisionResponse(
        service_id=service.id_servicio,
        previous_state=previous_state,
        new_state=service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        confirmed_at=None,
        duration_seconds=None,
        final_evidence_count=final_evidence_count,
        message="Service finalization rejected and returned to repair.",
    )
