from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from io import StringIO
from typing import Literal

from fastapi import HTTPException, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Administrador,
    Bitacora,
    Calificacion,
    Incidente,
    Notificacion,
    Operario,
    Pago,
    Servicio,
    SolicitudServicio,
    Taller,
    Usuario,
)
from app.packages.operaciones_taller.dependencies import WorkshopAdminContext

from .schemas import (
    AuditActorSummary,
    AuditLinkedEntitiesResponse,
    AuditLogDetailResponse,
    AuditLogFilterOptionsResponse,
    AuditLogItemResponse,
    AuditLogPageResponse,
    AuditTimelineItemResponse,
    AllowedRatingTargetResponse,
    ExistingRatingResponse,
    RatingReminderResponse,
    ServiceRatingRequest,
    ServiceRatingResponse,
    ServiceRatingStatusResponse,
)


PAID_SERVICE_STATE = "PAGADO"
AUDIT_CONFIGURATION_EVENT_TYPES = {"CONFIGURACION_TALLER", "GESTION_PERSONAL"}
AUDIT_TIMELINE_EVENT_TYPES = {
    "TRIAJE",
    "MATCHMAKING",
    "OPERACION_TALLER",
    "OPERACION_CAMPO",
    "IA",
    "PAGO",
    "NOTIFICACION",
    "REPUTACION",
    "CONFIGURACION_TALLER",
}


def _build_service_query():
    return select(Servicio).options(
        joinedload(Servicio.operario).joinedload(Operario.persona),
        joinedload(Servicio.solicitud).joinedload(SolicitudServicio.taller),
        joinedload(Servicio.solicitud).joinedload(SolicitudServicio.incidente),
        joinedload(Servicio.calificaciones),
    )


def _build_audit_query():
    return select(Bitacora).options(
        joinedload(Bitacora.usuario).joinedload(Usuario.persona),
    )


def _get_workshop_owned_service(
    db: Session,
    *,
    service_id: int,
    workshop_id: int,
) -> Servicio:
    service = db.scalar(
        _build_service_query()
        .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
        .where(
            Servicio.id_servicio == service_id,
            SolicitudServicio.id_taller == workshop_id,
        )
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop service not found.",
        )
    return service


def _build_workshop_visible_audit_query(
    *,
    admin_context: WorkshopAdminContext,
):
    workshop_id = admin_context.workshop_id
    visible_service_ids = (
        select(Servicio.id_servicio)
        .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
        .where(SolicitudServicio.id_taller == workshop_id)
    )
    visible_request_ids = select(SolicitudServicio.id_solicitud).where(
        SolicitudServicio.id_taller == workshop_id
    )
    visible_incident_ids = select(SolicitudServicio.id_incidente).where(
        SolicitudServicio.id_taller == workshop_id
    )
    visible_payment_ids = (
        select(Pago.id_pago)
        .join(Servicio, Servicio.id_servicio == Pago.id_servicio)
        .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
        .where(SolicitudServicio.id_taller == workshop_id)
    )
    visible_admin_user_ids = (
        select(Usuario.id_usuario)
        .join(Administrador, Administrador.id_persona == Usuario.id_persona)
        .where(
            Administrador.id_taller == workshop_id,
            Administrador.activo.is_(True),
            Usuario.activo.is_(True),
        )
    )
    visibility_clause = or_(
        Bitacora.id_servicio.in_(visible_service_ids),
        Bitacora.id_solicitud.in_(visible_request_ids),
        Bitacora.id_pago.in_(visible_payment_ids),
        and_(
            Bitacora.id_incidente.in_(visible_incident_ids),
            Bitacora.id_solicitud.is_(None),
            Bitacora.id_servicio.is_(None),
            Bitacora.id_pago.is_(None),
        ),
        and_(
            Bitacora.id_usuario.in_(visible_admin_user_ids),
            Bitacora.tipo_evento.in_(tuple(AUDIT_CONFIGURATION_EVENT_TYPES)),
        ),
    )
    return _build_audit_query().where(visibility_clause)


def _validate_audit_filters(
    *,
    limit: int,
    offset: int,
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 100.",
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset must be greater than or equal to 0.",
        )
    if date_from is not None and date_to is not None and date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be greater than or equal to date_from.",
        )


def _apply_audit_filters(
    query,
    *,
    service_id: int | None = None,
    incident_id: int | None = None,
    request_id: int | None = None,
    payment_id: int | None = None,
    actor_user_id: int | None = None,
    event_type: str | None = None,
    action: str | None = None,
    main_entity: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
):
    if service_id is not None:
        query = query.where(Bitacora.id_servicio == service_id)
    if incident_id is not None:
        query = query.where(Bitacora.id_incidente == incident_id)
    if request_id is not None:
        query = query.where(Bitacora.id_solicitud == request_id)
    if payment_id is not None:
        query = query.where(Bitacora.id_pago == payment_id)
    if actor_user_id is not None:
        query = query.where(Bitacora.id_usuario == actor_user_id)
    if event_type is not None:
        query = query.where(Bitacora.tipo_evento == event_type.strip())
    if action is not None:
        query = query.where(Bitacora.accion == action.strip())
    if main_entity is not None:
        query = query.where(Bitacora.entidad_principal == main_entity.strip())
    if date_from is not None:
        query = query.where(Bitacora.fecha_hora >= date_from)
    if date_to is not None:
        query = query.where(Bitacora.fecha_hora <= date_to)
    normalized_search = " ".join(search.split()) if search is not None else None
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.where(
            or_(
                Bitacora.accion.ilike(pattern),
                Bitacora.tipo_evento.ilike(pattern),
                Bitacora.descripcion.ilike(pattern),
                Bitacora.entidad_principal.ilike(pattern),
                Bitacora.hash_evento.ilike(pattern),
            )
        )
    return query


def _serialize_audit_actor(user: Usuario | None) -> AuditActorSummary | None:
    if user is None:
        return None
    return AuditActorSummary(
        user_id=user.id_usuario,
        persona_id=user.id_persona,
        email=user.email,
        tipo_usuario=user.tipo_usuario,
    )


def _serialize_audit_linked(event: Bitacora) -> AuditLinkedEntitiesResponse:
    return AuditLinkedEntitiesResponse(
        incident_id=event.id_incidente,
        request_id=event.id_solicitud,
        service_id=event.id_servicio,
        payment_id=event.id_pago,
    )


def _serialize_audit_item(event: Bitacora) -> AuditLogItemResponse:
    return AuditLogItemResponse(
        audit_id=event.id_bitacora,
        timestamp=event.fecha_hora,
        action=event.accion,
        event_type=event.tipo_evento,
        description=event.descripcion,
        main_entity=event.entidad_principal,
        main_entity_id=event.id_entidad_principal,
        actor=_serialize_audit_actor(event.usuario),
        linked=_serialize_audit_linked(event),
        hash_evento=event.hash_evento,
        has_original_data=event.datos_originales is not None,
        has_new_data=event.datos_nuevos is not None,
    )


def _serialize_audit_detail(event: Bitacora) -> AuditLogDetailResponse:
    item = _serialize_audit_item(event)
    return AuditLogDetailResponse(
        **item.model_dump(),
        datos_originales=event.datos_originales,
        datos_nuevos=event.datos_nuevos,
        ip_origen=event.ip_origen,
        user_agent=event.user_agent,
    )


def _extract_state_from_payload(payload: object, *keys: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _serialize_timeline_item(event: Bitacora) -> AuditTimelineItemResponse:
    return AuditTimelineItemResponse(
        audit_id=event.id_bitacora,
        timestamp=event.fecha_hora,
        action=event.accion,
        event_type=event.tipo_evento,
        description=event.descripcion,
        service_state=(
            _extract_state_from_payload(
                event.datos_nuevos,
                "new_state",
                "service_state",
                "service_new_state",
            )
            or _extract_state_from_payload(event.datos_originales, "service_state")
        ),
        incident_state=(
            _extract_state_from_payload(
                event.datos_nuevos,
                "incident_new_state",
                "incident_state",
                "new_incident_state",
            )
            or _extract_state_from_payload(event.datos_originales, "incident_state")
        ),
    )


def _get_client_owned_service(db: Session, *, service_id: int, cliente_id: int) -> Servicio:
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


def _get_operario_owned_service(db: Session, *, service_id: int, operario_id: int) -> Servicio:
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


def _validate_rating_eligible(service: Servicio) -> None:
    if service.estado != PAID_SERVICE_STATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service must be paid before it can be rated.",
        )


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


def _get_user_by_persona_id(db: Session, *, persona_id: int) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.id_persona == persona_id))


def _create_notification(
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


def _create_rating_bitacora(
    *,
    actor_user: Usuario,
    service: Servicio,
    action: str,
    description: str,
    payload: dict[str, object],
) -> Bitacora:
    incident = service.solicitud.incidente
    return Bitacora(
        accion=action,
        tipo_evento="REPUTACION",
        descripcion=description,
        entidad_principal="SERVICIO",
        id_entidad_principal=service.id_servicio,
        datos_nuevos=payload,
        hash_evento="",
        id_usuario=actor_user.id_usuario,
        id_incidente=incident.id_incidente,
        id_solicitud=service.id_solicitud,
        id_servicio=service.id_servicio,
    )


def _serialize_existing_rating(rating: Calificacion) -> ExistingRatingResponse:
    target_type = rating.receptor_tipo
    target_id = rating.id_taller_calif if rating.receptor_tipo == "TALLER" else rating.id_receptor
    return ExistingRatingResponse(
        rating_id=rating.id_calificacion,
        target_type=target_type,
        target_id=target_id,
        estrellas=rating.estrellas,
        comentario=rating.comentario,
        fecha=rating.fecha,
    )


def _get_allowed_targets(service: Servicio, actor_type: str) -> list[AllowedRatingTargetResponse]:
    if actor_type == "CLIENTE":
        targets = [
            AllowedRatingTargetResponse(
                target_type="TALLER",
                target_id=service.solicitud.id_taller,
                label=service.solicitud.taller.nombre_comercial,
            )
        ]
        if service.id_persona_operario is not None and service.operario is not None:
            targets.append(
                AllowedRatingTargetResponse(
                    target_type="PERSONA",
                    target_id=service.id_persona_operario,
                    label=(
                        f"{service.operario.persona.nombre} {service.operario.persona.apellido}"
                    ),
                )
            )
        return targets

    incident = service.solicitud.incidente
    return [
        AllowedRatingTargetResponse(
            target_type="PERSONA",
            target_id=incident.id_cliente,
            label="CLIENTE",
        )
    ]


def _get_existing_ratings_for_actor(
    service: Servicio,
    *,
    actor_persona_id: int,
) -> list[Calificacion]:
    return [item for item in service.calificaciones if item.id_emisor == actor_persona_id]


def _get_pending_targets(
    service: Servicio,
    *,
    actor_user: Usuario,
) -> list[AllowedRatingTargetResponse]:
    allowed_targets = _get_allowed_targets(service, actor_user.tipo_usuario)
    existing_ratings = _get_existing_ratings_for_actor(
        service,
        actor_persona_id=actor_user.id_persona,
    )
    pending_targets: list[AllowedRatingTargetResponse] = []
    for target in allowed_targets:
        already_rated = False
        for rating in existing_ratings:
            rating_target_type = rating.receptor_tipo
            rating_target_id = (
                rating.id_taller_calif if rating_target_type == "TALLER" else rating.id_receptor
            )
            if rating_target_type == target.target_type and rating_target_id == target.target_id:
                already_rated = True
                break
        if not already_rated:
            pending_targets.append(target)
    return pending_targets


def _reminder_payload(
    *,
    service: Servicio,
    actor_user: Usuario,
    pending_targets: list[AllowedRatingTargetResponse],
) -> dict[str, object]:
    return {
        "service_id": service.id_servicio,
        "incident_id": service.solicitud.incidente.id_incidente,
        "actor_type": actor_user.tipo_usuario,
        "pending_targets": [item.model_dump() for item in pending_targets],
    }


def _has_equivalent_pending_reminder(
    db: Session,
    *,
    user_id: int,
    service_id: int,
    payload: dict[str, object],
) -> bool:
    notifications = list(
        db.scalars(
            select(Notificacion).where(
                Notificacion.id_usuario == user_id,
                Notificacion.id_servicio == service_id,
                Notificacion.estado == "PENDIENTE",
                Notificacion.titulo == "Recordatorio de calificacion pendiente",
            )
        )
    )
    for item in notifications:
        if item.payload == payload:
            return True
    return False


def list_workshop_audit_logs(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
    service_id: int | None = None,
    incident_id: int | None = None,
    request_id: int | None = None,
    payment_id: int | None = None,
    actor_user_id: int | None = None,
    event_type: str | None = None,
    action: str | None = None,
    main_entity: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditLogPageResponse:
    _validate_audit_filters(limit=limit, offset=offset, date_from=date_from, date_to=date_to)
    filtered_query = _apply_audit_filters(
        _build_workshop_visible_audit_query(admin_context=admin_context),
        service_id=service_id,
        incident_id=incident_id,
        request_id=request_id,
        payment_id=payment_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        action=action,
        main_entity=main_entity,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    total = db.scalar(
        select(func.count()).select_from(filtered_query.order_by(None).subquery())
    ) or 0
    items = list(
        db.scalars(
            filtered_query
            .order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return AuditLogPageResponse(
        items=[_serialize_audit_item(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        has_next=offset + len(items) < total,
    )


def get_workshop_audit_log_detail(
    *,
    audit_id: int,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> AuditLogDetailResponse:
    event = db.scalar(
        _build_workshop_visible_audit_query(admin_context=admin_context).where(
            Bitacora.id_bitacora == audit_id
        )
    )
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log event not found.",
        )
    return _serialize_audit_detail(event)


def get_workshop_service_timeline(
    *,
    service_id: int,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> list[AuditTimelineItemResponse]:
    service = _get_workshop_owned_service(
        db,
        service_id=service_id,
        workshop_id=admin_context.workshop_id,
    )
    payment_id = service.pago.id_pago if service.pago is not None else None
    link_conditions = [
        Bitacora.id_servicio == service.id_servicio,
        Bitacora.id_solicitud == service.id_solicitud,
        Bitacora.id_incidente == service.solicitud.incidente.id_incidente,
    ]
    if payment_id is not None:
        link_conditions.append(Bitacora.id_pago == payment_id)
    timeline_query = _build_workshop_visible_audit_query(admin_context=admin_context).where(
        Bitacora.tipo_evento.in_(tuple(AUDIT_TIMELINE_EVENT_TYPES)),
        or_(*link_conditions),
    )
    events = list(
        db.scalars(
            timeline_query.order_by(Bitacora.fecha_hora.asc(), Bitacora.id_bitacora.asc())
        )
    )
    return [_serialize_timeline_item(event) for event in events]


def get_workshop_audit_filter_options(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> AuditLogFilterOptionsResponse:
    visible_subquery = _build_workshop_visible_audit_query(
        admin_context=admin_context
    ).order_by(None).subquery()
    event_types = [
        value
        for value in db.scalars(
            select(visible_subquery.c.tipo_evento)
            .distinct()
            .order_by(visible_subquery.c.tipo_evento.asc())
        )
        if value is not None
    ]
    actions = [
        value
        for value in db.scalars(
            select(visible_subquery.c.accion)
            .distinct()
            .order_by(visible_subquery.c.accion.asc())
        )
        if value is not None
    ]
    main_entities = [
        value
        for value in db.scalars(
            select(visible_subquery.c.entidad_principal)
            .distinct()
            .order_by(visible_subquery.c.entidad_principal.asc())
        )
        if value is not None
    ]
    return AuditLogFilterOptionsResponse(
        event_types=event_types,
        actions=actions,
        main_entities=main_entities,
    )


def export_workshop_audit_logs_csv(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
    service_id: int | None = None,
    incident_id: int | None = None,
    request_id: int | None = None,
    payment_id: int | None = None,
    actor_user_id: int | None = None,
    event_type: str | None = None,
    action: str | None = None,
    main_entity: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
) -> Response:
    _validate_audit_filters(limit=50, offset=0, date_from=date_from, date_to=date_to)
    filtered_query = _apply_audit_filters(
        _build_workshop_visible_audit_query(admin_context=admin_context),
        service_id=service_id,
        incident_id=incident_id,
        request_id=request_id,
        payment_id=payment_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        action=action,
        main_entity=main_entity,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    events = list(
        db.scalars(
            filtered_query.order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
        )
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "audit_id",
            "timestamp",
            "action",
            "event_type",
            "description",
            "main_entity",
            "main_entity_id",
            "user_id",
            "incident_id",
            "request_id",
            "service_id",
            "payment_id",
            "hash_evento",
            "ip_origen",
        ]
    )
    for event in events:
        writer.writerow(
            [
                event.id_bitacora,
                event.fecha_hora.isoformat(),
                event.accion,
                event.tipo_evento,
                event.descripcion,
                event.entidad_principal,
                event.id_entidad_principal,
                event.id_usuario,
                event.id_incidente,
                event.id_solicitud,
                event.id_servicio,
                event.id_pago,
                event.hash_evento,
                event.ip_origen,
            ]
        )
    filename = f"audit_logs_workshop_{admin_context.workshop_id}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def get_rating_status(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> ServiceRatingStatusResponse:
    if current_user.tipo_usuario == "CLIENTE":
        service = _get_client_owned_service(db, service_id=service_id, cliente_id=current_user.id_persona)
    elif current_user.tipo_usuario == "OPERARIO":
        service = _get_operario_owned_service(db, service_id=service_id, operario_id=current_user.id_persona)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for CLIENTE or OPERARIO.",
        )

    _validate_rating_eligible(service)

    existing = [
        _serialize_existing_rating(item)
        for item in _get_existing_ratings_for_actor(
            service,
            actor_persona_id=current_user.id_persona,
        )
    ]
    return ServiceRatingStatusResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=service.solicitud.incidente.id_incidente,
        actor_type=current_user.tipo_usuario,
        allowed_targets=_get_allowed_targets(service, current_user.tipo_usuario),
        existing_ratings=existing,
    )


def create_rating_reminder(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> RatingReminderResponse:
    if current_user.tipo_usuario == "CLIENTE":
        service = _get_client_owned_service(db, service_id=service_id, cliente_id=current_user.id_persona)
    elif current_user.tipo_usuario == "OPERARIO":
        service = _get_operario_owned_service(db, service_id=service_id, operario_id=current_user.id_persona)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for CLIENTE or OPERARIO.",
        )

    _validate_rating_eligible(service)
    pending_targets = _get_pending_targets(service, actor_user=current_user)
    incident = service.solicitud.incidente

    if not pending_targets:
        return RatingReminderResponse(
            service_id=service.id_servicio,
            actor_type=current_user.tipo_usuario,
            incident_id=incident.id_incidente,
            pending_targets=[],
            reminder_created=False,
            message="All allowed ratings were already submitted for this service.",
        )

    payload = _reminder_payload(
        service=service,
        actor_user=current_user,
        pending_targets=pending_targets,
    )
    if _has_equivalent_pending_reminder(
        db,
        user_id=current_user.id_usuario,
        service_id=service.id_servicio,
        payload=payload,
    ):
        return RatingReminderResponse(
            service_id=service.id_servicio,
            actor_type=current_user.tipo_usuario,
            incident_id=incident.id_incidente,
            pending_targets=pending_targets,
            reminder_created=False,
            message="An equivalent pending rating reminder already exists.",
        )

    _create_notification(
        db=db,
        user=current_user,
        service=service,
        title="Recordatorio de calificacion pendiente",
        message="Aun tienes calificaciones pendientes para este servicio.",
        payload=payload,
    )
    db.add(
        _create_rating_bitacora(
            actor_user=current_user,
            service=service,
            action="RECORDATORIO_CALIFICACION_GENERADO",
            description="Se genero un recordatorio de calificacion pendiente para el actor del servicio.",
            payload=payload,
        )
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rating reminder could not be persisted.",
        ) from exc

    return RatingReminderResponse(
        service_id=service.id_servicio,
        actor_type=current_user.tipo_usuario,
        incident_id=incident.id_incidente,
        pending_targets=pending_targets,
        reminder_created=True,
        message="Rating reminder created successfully.",
    )


def _resolve_target(
    *,
    service: Servicio,
    actor_user: Usuario,
    payload: ServiceRatingRequest,
) -> tuple[str, Literal["PERSONA", "TALLER"], int | None, int | None]:
    incident = service.solicitud.incidente
    if actor_user.tipo_usuario == "CLIENTE":
        if payload.target_type == "TALLER":
            if payload.target_id not in {None, service.solicitud.id_taller}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Target workshop does not match this service.",
                )
            return "CLIENTE", "TALLER", None, service.solicitud.id_taller
        if service.id_persona_operario is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Service does not have an assigned operario to rate.",
            )
        if payload.target_id != service.id_persona_operario:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Target persona does not match the assigned operario.",
            )
        return "CLIENTE", "PERSONA", service.id_persona_operario, None

    if actor_user.tipo_usuario == "OPERARIO":
        if payload.target_type != "PERSONA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Operario can only rate the client as PERSONA.",
            )
        if payload.target_id != incident.id_cliente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Target persona does not match the service client.",
            )
        return "OPERARIO", "PERSONA", incident.id_cliente, None

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This endpoint is only available for CLIENTE or OPERARIO.",
    )


def _find_existing_rating(
    *,
    service: Servicio,
    actor_user: Usuario,
    receptor_tipo: str,
    id_receptor: int | None,
    id_taller_calif: int | None,
) -> Calificacion | None:
    for item in service.calificaciones:
        if (
            item.id_emisor == actor_user.id_persona
            and item.receptor_tipo == receptor_tipo
            and item.id_receptor == id_receptor
            and item.id_taller_calif == id_taller_calif
        ):
            return item
    return None


def _recalculate_taller_reputation(db: Session, *, taller_id: int) -> Decimal | None:
    avg_value = db.scalar(
        select(func.avg(Calificacion.estrellas))
        .where(
            Calificacion.receptor_tipo == "TALLER",
            Calificacion.id_taller_calif == taller_id,
        )
    )
    taller = db.get(Taller, taller_id)
    if taller is None:
        return None
    reputacion = Decimal(avg_value).quantize(Decimal("0.01")) if avg_value is not None else None
    taller.reputacion_prom = reputacion
    return reputacion


def _recalculate_person_reputation(db: Session, *, persona_id: int) -> Decimal | None:
    avg_value = db.scalar(
        select(func.avg(Calificacion.estrellas))
        .where(
            Calificacion.receptor_tipo == "PERSONA",
            Calificacion.id_receptor == persona_id,
        )
    )
    user = _get_user_by_persona_id(db, persona_id=persona_id)
    if user is None:
        return None
    reputacion = Decimal(avg_value).quantize(Decimal("0.01")) if avg_value is not None else None
    user.reputacion_prom = reputacion
    return reputacion


def submit_service_rating(
    *,
    service_id: int,
    payload: ServiceRatingRequest,
    current_user: Usuario,
    db: Session,
) -> ServiceRatingResponse:
    if current_user.tipo_usuario == "CLIENTE":
        service = _get_client_owned_service(db, service_id=service_id, cliente_id=current_user.id_persona)
    elif current_user.tipo_usuario == "OPERARIO":
        service = _get_operario_owned_service(db, service_id=service_id, operario_id=current_user.id_persona)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for CLIENTE or OPERARIO.",
        )

    _validate_rating_eligible(service)
    emisor_tipo, receptor_tipo, id_receptor, id_taller_calif = _resolve_target(
        service=service,
        actor_user=current_user,
        payload=payload,
    )

    existing = _find_existing_rating(
        service=service,
        actor_user=current_user,
        receptor_tipo=receptor_tipo,
        id_receptor=id_receptor,
        id_taller_calif=id_taller_calif,
    )
    previous_rating = existing.estrellas if existing is not None else None
    updated_existing = existing is not None

    if existing is None:
        rating = Calificacion(
            id_servicio=service.id_servicio,
            id_emisor=current_user.id_persona,
            id_receptor=id_receptor,
            id_taller_calif=id_taller_calif,
            emisor_tipo=emisor_tipo,
            receptor_tipo=receptor_tipo,
            estrellas=payload.estrellas,
            comentario=payload.comentario,
        )
        db.add(rating)
    else:
        rating = existing
        rating.estrellas = payload.estrellas
        rating.comentario = payload.comentario
        rating.fecha = func.now()

    db.flush()
    recipient_reputation = None
    if receptor_tipo == "TALLER" and id_taller_calif is not None:
        recipient_reputation = _recalculate_taller_reputation(db, taller_id=id_taller_calif)
    elif receptor_tipo == "PERSONA" and id_receptor is not None:
        recipient_reputation = _recalculate_person_reputation(db, persona_id=id_receptor)

    action = "CALIFICACION_ACTUALIZADA" if updated_existing else "CALIFICACION_REGISTRADA"
    db.add(
        _create_rating_bitacora(
            actor_user=current_user,
            service=service,
            action=action,
            description="Se registro o actualizo una calificacion general del servicio.",
            payload={
                "service_id": service.id_servicio,
                "actor_type": current_user.tipo_usuario,
                "target_type": receptor_tipo,
                "target_id": id_receptor,
                "workshop_id": id_taller_calif,
                "previous_rating": previous_rating,
                "new_rating": payload.estrellas,
            },
        )
    )

    if receptor_tipo == "TALLER" and id_taller_calif is not None:
        for admin_user in _get_workshop_admin_users(db, workshop_id=id_taller_calif):
            _create_notification(
                db=db,
                user=admin_user,
                service=service,
                title="Nuevo puntaje para el taller",
                message=f"El cliente califico el taller con {payload.estrellas} estrellas.",
                payload={
                    "service_id": service.id_servicio,
                    "rating_id": getattr(rating, "id_calificacion", None),
                    "target_type": receptor_tipo,
                    "workshop_id": id_taller_calif,
                    "estrellas": payload.estrellas,
                },
            )
    elif receptor_tipo == "PERSONA" and id_receptor is not None:
        recipient_user = _get_user_by_persona_id(db, persona_id=id_receptor)
        if recipient_user is not None:
            _create_notification(
                db=db,
                user=recipient_user,
                service=service,
                title="Nueva calificacion recibida",
                message=f"Recibiste una calificacion de {payload.estrellas} estrellas.",
                payload={
                    "service_id": service.id_servicio,
                    "rating_id": getattr(rating, "id_calificacion", None),
                    "target_type": receptor_tipo,
                    "target_id": id_receptor,
                    "estrellas": payload.estrellas,
                },
            )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rating conflicts with an existing submission.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rating could not be persisted.",
        ) from exc

    db.refresh(rating)
    return ServiceRatingResponse(
        service_id=service.id_servicio,
        actor_type=current_user.tipo_usuario,
        target_type=receptor_tipo,
        target_id=id_taller_calif if receptor_tipo == "TALLER" else id_receptor,
        estrellas=rating.estrellas,
        comentario=rating.comentario,
        rating_id=rating.id_calificacion,
        updated_existing=updated_existing,
        recipient_reputation=recipient_reputation,
        message=(
            "Rating updated successfully."
            if updated_existing
            else "Rating created successfully."
        ),
    )
