from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Administrador,
    Bitacora,
    Calificacion,
    Incidente,
    Notificacion,
    Operario,
    Servicio,
    SolicitudServicio,
    Taller,
    Usuario,
)

from .schemas import (
    AllowedRatingTargetResponse,
    ExistingRatingResponse,
    RatingReminderResponse,
    ServiceRatingRequest,
    ServiceRatingResponse,
    ServiceRatingStatusResponse,
)


PAID_SERVICE_STATE = "PAGADO"


def _build_service_query():
    return select(Servicio).options(
        joinedload(Servicio.operario).joinedload(Operario.persona),
        joinedload(Servicio.solicitud).joinedload(SolicitudServicio.taller),
        joinedload(Servicio.solicitud).joinedload(SolicitudServicio.incidente),
        joinedload(Servicio.calificaciones),
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
