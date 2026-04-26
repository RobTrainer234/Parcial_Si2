from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Administrador,
    Bitacora,
    CatalogoServicioTaller,
    Evidencia,
    Especialidad,
    Incidente,
    Notificacion,
    Operario,
    OperarioEspecialidad,
    Persona,
    Servicio,
    ServicioInforme,
    ServicioRepuesto,
    SolicitudServicio,
    Taller,
    TallerArchivo,
    TallerEspecialidad,
    Usuario,
)
from app.packages.seguridad_usuarios.security import hash_password
from app.packages.inteligencia_triaje.matchmaking import build_ranked_candidate
from app.packages.inteligencia_triaje.service import rematch_incident_after_workshop_rejection
from app.packages.inteligencia_triaje.storage import (
    IMAGE_MIME_PREFIX,
    StorageError,
    StoredMedia,
    get_triage_storage,
)
from app.packages.seguridad_usuarios.security import utc_now

from .dependencies import WorkshopAdminContext
from .schemas import (
    AssignedOperarioSummary,
    AssignOperarioRequest,
    AssignOperarioResponse,
    FinalEvidenceResponse,
    OperarioCandidateSummary,
    RepairReportItemInput,
    RepairReportSaveResponse,
    RepairReportSnapshotResponse,
    SpecialtySummaryResponse,
    StaffSpecialtyResponse,
    UsedSparePartResponse,
    WaitingAssignmentServiceSummary,
    WorkshopRequestDecisionRequest,
    WorkshopRequestDecisionResponse,
    WorkshopRequestDetailResponse,
    WorkshopCatalogServiceCreateRequest,
    WorkshopCatalogServiceResponse,
    WorkshopCatalogServiceUpdateRequest,
    WorkshopConfiguredSpecialtyResponse,
    WorkshopMediaFileResponse,
    WorkshopMediaUploadRequest,
    WorkshopProfileResponse,
    WorkshopProfileUpdateRequest,
    WorkshopRequestSummary,
    WorkshopSummaryResponse,
    WorkshopStaffAvailabilityUpdateRequest,
    WorkshopStaffCreateRequest,
    WorkshopStaffSummary,
)


WAITING_ASSIGNMENT_SERVICE_STATE = "EN_ESPERA_ASIGNACION"
ASSIGNED_SERVICE_STATE = "ASIGNADO"
ELIGIBLE_PRE_ASSIGNMENT_SERVICE_STATES = {WAITING_ASSIGNMENT_SERVICE_STATE}
AVAILABLE_OPERARIO_STATES = {"DISPONIBLE"}
OPERARIO_AVAILABILITY_ALLOWED_STATES = {"DISPONIBLE", "EN_SERVICIO", "NO_DISPONIBLE", "BAJA"}
REPAIR_REPORT_SAVE_ALLOWED_STATES = {"EN_REPARACION", "COMPLETADO_PENDIENTE_CONFIRMACION"}
REPAIR_REPORT_NEXT_STATE = "COMPLETADO_PENDIENTE_CONFIRMACION"
REPORT_NOTES_VERSION = 1
WORKSHOP_IMAGE_MIME_PREFIX = "image/"
WORKSHOP_CERTIFICATE_ALLOWED_MIME_PREFIXES = ("application/pdf", "image/")
PREQUOTATION_CURRENCY = "BOB"
PREQUOTATION_SEVERITY_FACTORS: dict[str, Decimal] = {
    "BAJA": Decimal("1.00"),
    "MEDIA": Decimal("1.15"),
    "ALTA": Decimal("1.35"),
    "CRITICA": Decimal("1.60"),
}
PREQUOTATION_MIN_FACTOR = Decimal("1.00")
PREQUOTATION_MAX_FACTOR = Decimal("1.80")
PREQUOTATION_HISTORICAL_SERVICE_STATES = {
    "COMPLETADO_PENDIENTE_CONFIRMACION",
    "FINALIZADO_PENDIENTE_PAGO",
    "PAGADO",
}


def _build_request_query():
    return select(SolicitudServicio).options(
        joinedload(SolicitudServicio.taller),
        joinedload(SolicitudServicio.servicio),
        joinedload(SolicitudServicio.incidente).joinedload(Incidente.especialidad_reportada_cliente),
        joinedload(SolicitudServicio.incidente).joinedload(Incidente.especialidad_detectada),
    )


def _build_service_query():
    return select(Servicio).options(
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.taller),
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.incidente)
        .joinedload(Incidente.especialidad_detectada),
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.incidente)
        .joinedload(Incidente.especialidad_reportada_cliente),
        joinedload(Servicio.operario).joinedload(Operario.persona),
    )


def _build_repair_service_query():
    return select(Servicio).options(
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.taller),
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.incidente)
        .joinedload(Incidente.especialidad_detectada),
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.incidente)
        .joinedload(Incidente.especialidad_reportada_cliente),
        joinedload(Servicio.operario).joinedload(Operario.persona),
        joinedload(Servicio.informe),
        selectinload(Servicio.repuestos),
        selectinload(Servicio.evidencias),
    )


def _build_operario_query():
    return select(Operario).options(
        joinedload(Operario.persona),
        joinedload(Operario.persona).joinedload(Persona.usuario),
        joinedload(Operario.especialidades).joinedload(OperarioEspecialidad.especialidad),
    )


def _build_workshop_profile_query():
    return select(Taller).options(
        selectinload(Taller.especialidades).joinedload(TallerEspecialidad.especialidad),
        selectinload(Taller.archivos),
    )


def _build_workshop_catalog_query():
    return select(CatalogoServicioTaller).options(
        joinedload(CatalogoServicioTaller.especialidad),
    )


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_text(value)
    return normalized or None


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_phone(phone: str | None) -> str | None:
    if phone is None:
        return None
    normalized = phone.strip()
    return normalized or None


def _normalize_catalog_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_text(value).upper()
    return normalized or None


def _quantize_currency(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _build_staff_specialty_response(association: OperarioEspecialidad) -> StaffSpecialtyResponse:
    return StaffSpecialtyResponse(
        id_especialidad=association.especialidad.id_especialidad,
        nombre=association.especialidad.nombre,
        anios_experiencia=association.anios_experiencia,
        certificacion_url=association.certificacion_url,
    )


def _build_workshop_staff_summary(operario: Operario) -> WorkshopStaffSummary:
    persona = operario.persona
    usuario = persona.usuario
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Operario user account is not provisioned.",
        )
    return WorkshopStaffSummary(
        operario_id=operario.id_persona,
        persona_id=operario.id_persona,
        nombre_completo=f"{persona.nombre} {persona.apellido}",
        ci=persona.ci,
        email=usuario.email,
        telefono=persona.telefono,
        estado_disponibilidad=operario.estado_disponibilidad,
        activo=operario.activo,
        specialties=[
            _build_staff_specialty_response(association)
            for association in sorted(
                operario.especialidades,
                key=lambda item: item.id_especialidad,
            )
        ],
        registered_at=operario.created_at,
    )


def _build_workshop_configured_specialty_response(
    association: TallerEspecialidad,
) -> WorkshopConfiguredSpecialtyResponse:
    return WorkshopConfiguredSpecialtyResponse(
        id_especialidad=association.especialidad.id_especialidad,
        nombre=association.especialidad.nombre,
        activo=association.activo,
    )


def _build_workshop_profile_response(taller: Taller) -> WorkshopProfileResponse:
    specialties = [
        _build_workshop_configured_specialty_response(association)
        for association in sorted(
            taller.especialidades,
            key=lambda item: item.id_especialidad,
        )
        if association.activo
    ]
    active_files = sorted(
        [item for item in taller.archivos if item.activo],
        key=lambda item: (item.fecha_registro, item.id_taller_archivo),
        reverse=True,
    )
    return WorkshopProfileResponse(
        workshop_id=taller.id_taller,
        nombre_comercial=taller.nombre_comercial,
        descripcion=taller.descripcion,
        latitud=taller.latitud,
        longitud=taller.longitud,
        radio_accion_km=taller.radio_accion_km,
        activo=taller.activo,
        acepta_seguro_propio=taller.acepta_seguro_propio,
        specialties=specialties,
        imagenes_taller=[
            _serialize_workshop_media_file(item)
            for item in active_files
            if item.tipo_archivo == "IMAGEN_TALLER"
        ],
        certificados_tecnicos=[
            _serialize_workshop_media_file(item)
            for item in active_files
            if item.tipo_archivo == "CERTIFICADO_TECNICO"
        ],
    )


def _serialize_workshop_catalog_service(
    item: CatalogoServicioTaller,
) -> WorkshopCatalogServiceResponse:
    return WorkshopCatalogServiceResponse(
        catalog_id=item.id_catalogo_servicio,
        workshop_id=item.id_taller,
        id_especialidad=item.id_especialidad,
        especialidad_nombre=item.especialidad.nombre,
        nombre=item.nombre,
        descripcion=item.descripcion,
        precio_base_min=item.precio_base_min,
        precio_base_max=item.precio_base_max,
        incluye_repuestos_basicos=item.incluye_repuestos_basicos,
        activo=item.activo,
    )


def _get_admin_workshop(
    *,
    db: Session,
    workshop_id: int,
) -> Taller:
    taller = db.scalar(
        _build_workshop_profile_query().where(Taller.id_taller == workshop_id)
    )
    if taller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found.",
    )
    return taller


def _serialize_workshop_media_file(item: TallerArchivo) -> WorkshopMediaFileResponse:
    return WorkshopMediaFileResponse(
        id_taller_archivo=item.id_taller_archivo,
        tipo_archivo=item.tipo_archivo,
        nombre_archivo=item.nombre_archivo,
        url_archivo=item.url_archivo,
        mime_type=item.mime_type,
        tamano_bytes=item.tamano_bytes,
        fecha_registro=item.fecha_registro,
        descripcion=item.descripcion,
        activo=item.activo,
    )


def _get_workshop_media_file(
    *,
    db: Session,
    file_id: int,
    workshop_id: int,
) -> TallerArchivo:
    file_row = db.scalar(
        select(TallerArchivo).where(
            TallerArchivo.id_taller_archivo == file_id,
            TallerArchivo.id_taller == workshop_id,
        )
    )
    if file_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop media file not found.",
        )
    return file_row


def _get_workshop_catalog_service(
    *,
    db: Session,
    catalog_id: int,
    workshop_id: int,
) -> CatalogoServicioTaller:
    catalog_row = db.scalar(
        _build_workshop_catalog_query().where(
            CatalogoServicioTaller.id_catalogo_servicio == catalog_id,
            CatalogoServicioTaller.id_taller == workshop_id,
        )
    )
    if catalog_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop catalog service not found.",
        )
    return catalog_row


def _get_latest_prequotation_payload(
    *,
    db: Session,
    service_id: int,
) -> dict[str, Any] | None:
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


def _get_catalog_service_name_from_prequotation(
    *,
    db: Session,
    service: Servicio | None,
) -> str | None:
    if service is None or service.codigo_precotizacion is None:
        return None
    payload = _get_latest_prequotation_payload(db=db, service_id=service.id_servicio)
    if payload is None or payload.get("catalog_service_name") is None:
        return None
    return str(payload["catalog_service_name"])


def _validate_workshop_media_upload(
    *,
    tipo_archivo: str,
    file: UploadFile,
) -> None:
    content_type = file.content_type or ""
    if tipo_archivo == "IMAGEN_TALLER":
        if not content_type.startswith(WORKSHOP_IMAGE_MIME_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workshop image must be an image file.",
            )
        return

    if not any(
        content_type == prefix or content_type.startswith(prefix)
        for prefix in WORKSHOP_CERTIFICATE_ALLOWED_MIME_PREFIXES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Technical certificate must be a PDF or image file.",
        )


def _create_workshop_media_bitacora(
    *,
    admin_context: WorkshopAdminContext,
    accion: str,
    descripcion: str,
    taller: Taller,
    file_row: TallerArchivo,
    ip_origen: str | None,
    user_agent: str | None,
) -> Bitacora:
    return Bitacora(
        accion=accion,
        tipo_evento="CONFIGURACION_TALLER",
        descripcion=descripcion,
        entidad_principal="USUARIO",
        id_entidad_principal=admin_context.user.id_usuario,
        datos_nuevos={
            "workshop_id": taller.id_taller,
            "file_id": file_row.id_taller_archivo,
            "tipo_archivo": file_row.tipo_archivo,
            "nombre_archivo": file_row.nombre_archivo,
        },
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=admin_context.user.id_usuario,
    )


def _get_workshop_operario(
    *,
    db: Session,
    operario_id: int,
    workshop_id: int,
) -> Operario:
    operario = (
        db.execute(
            _build_operario_query().where(
                Operario.id_persona == operario_id,
                Operario.id_taller == workshop_id,
            )
        )
        .unique()
        .scalars()
        .one_or_none()
    )
    if operario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop operario not found.",
        )
    return operario


def _ensure_staff_email_unique(db: Session, email: str) -> None:
    exists = db.scalar(
        select(Usuario.id_usuario).where(func.lower(Usuario.email) == _normalize_email(email))
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists.",
        )


def _ensure_staff_ci_unique(db: Session, ci: str) -> None:
    exists = db.scalar(
        select(Persona.id_persona).where(Persona.ci == _normalize_text(ci))
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CI already exists.",
        )


def _ensure_staff_phone_unique(db: Session, telefono: str | None) -> None:
    normalized_phone = _normalize_phone(telefono)
    if normalized_phone is None:
        return
    exists = db.scalar(select(Persona.id_persona).where(Persona.telefono == normalized_phone))
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone already exists.",
        )


def _get_specialties_by_ids(
    db: Session,
    *,
    specialty_ids: list[int],
) -> dict[int, Especialidad]:
    if not specialty_ids:
        return {}
    specialties = list(
        db.scalars(
            select(Especialidad)
            .where(Especialidad.id_especialidad.in_(specialty_ids))
            .order_by(Especialidad.id_especialidad)
        )
    )
    specialty_map = {item.id_especialidad: item for item in specialties}
    missing_ids = sorted(set(specialty_ids) - set(specialty_map))
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown specialty ids: {missing_ids}",
        )
    return specialty_map


def _get_workshop_specialties_by_ids(
    db: Session,
    *,
    specialty_ids: list[int],
) -> dict[int, Especialidad]:
    if not specialty_ids:
        return {}
    specialties = list(
        db.scalars(
            select(Especialidad)
            .where(Especialidad.id_especialidad.in_(specialty_ids))
            .order_by(Especialidad.id_especialidad)
        )
    )
    specialty_map = {item.id_especialidad: item for item in specialties}
    missing_ids = sorted(set(specialty_ids) - set(specialty_map))
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown specialty ids: {missing_ids}",
        )
    return specialty_map


def _create_staff_bitacora_event(
    *,
    admin_context: WorkshopAdminContext,
    accion: str,
    descripcion: str,
    target_user_id: int | None,
    target_operario_id: int | None,
    datos_nuevos: dict[str, Any] | None,
    ip_origen: str | None,
    user_agent: str | None,
) -> Bitacora:
    return Bitacora(
        accion=accion,
        tipo_evento="GESTION_PERSONAL",
        descripcion=descripcion,
        entidad_principal="USUARIO",
        id_entidad_principal=target_user_id or target_operario_id,
        datos_nuevos=datos_nuevos,
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=admin_context.user.id_usuario,
    )


def _create_workshop_profile_bitacora_event(
    *,
    admin_context: WorkshopAdminContext,
    taller: Taller,
    datos_nuevos: dict[str, Any],
    ip_origen: str | None,
    user_agent: str | None,
) -> Bitacora:
    return Bitacora(
        accion="TALLER_PERFIL_ACTUALIZADO",
        tipo_evento="CONFIGURACION_TALLER",
        descripcion="El administrador actualizo el perfil operativo del taller.",
        entidad_principal="USUARIO",
        id_entidad_principal=admin_context.user.id_usuario,
        datos_nuevos=datos_nuevos,
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=admin_context.user.id_usuario,
    )


def _create_workshop_catalog_bitacora_event(
    *,
    admin_context: WorkshopAdminContext,
    accion: str,
    descripcion: str,
    datos_nuevos: dict[str, Any],
    datos_originales: dict[str, Any] | None,
    ip_origen: str | None,
    user_agent: str | None,
) -> Bitacora:
    return Bitacora(
        accion=accion,
        tipo_evento="CONFIGURACION_TALLER",
        descripcion=descripcion,
        entidad_principal="USUARIO",
        id_entidad_principal=admin_context.user.id_usuario,
        datos_originales=datos_originales,
        datos_nuevos=datos_nuevos,
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=admin_context.user.id_usuario,
    )


def _create_prequotation_bitacora_event(
    *,
    admin_context: WorkshopAdminContext,
    incident: Incidente,
    request_row: SolicitudServicio,
    service: Servicio,
    payload: dict[str, Any],
    ip_origen: str | None,
    user_agent: str | None,
) -> Bitacora:
    return Bitacora(
        accion="PRECOTIZACION_TECNICA_GENERADA",
        tipo_evento="IA",
        descripcion="Se genero una precotizacion tecnica auditable a partir del triaje y el catalogo del taller.",
        entidad_principal="SERVICIO",
        id_entidad_principal=service.id_servicio,
        datos_nuevos=payload,
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=admin_context.user.id_usuario,
        id_incidente=incident.id_incidente,
        id_solicitud=request_row.id_solicitud,
        id_servicio=service.id_servicio,
    )


def _ensure_catalog_specialty_exists(
    *,
    db: Session,
    specialty_id: int,
) -> Especialidad:
    specialty = db.scalar(
        select(Especialidad).where(Especialidad.id_especialidad == specialty_id)
    )
    if specialty is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown specialty id.",
        )
    return specialty


def _ensure_catalog_duplicate_rules(
    *,
    db: Session,
    workshop_id: int,
    specialty_id: int,
    normalized_name: str,
    exclude_catalog_id: int | None = None,
) -> None:
    duplicate_active_same_specialty = db.scalar(
        select(CatalogoServicioTaller.id_catalogo_servicio).where(
            CatalogoServicioTaller.id_taller == workshop_id,
            CatalogoServicioTaller.id_especialidad == specialty_id,
            func.lower(CatalogoServicioTaller.nombre) == normalized_name.lower(),
            CatalogoServicioTaller.activo.is_(True),
            CatalogoServicioTaller.id_catalogo_servicio != exclude_catalog_id
            if exclude_catalog_id is not None
            else True,
        )
    )
    if duplicate_active_same_specialty is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active catalog service with the same specialty and name already exists.",
        )

    duplicate_name_in_workshop = db.scalar(
        select(CatalogoServicioTaller.id_catalogo_servicio).where(
            CatalogoServicioTaller.id_taller == workshop_id,
            func.lower(CatalogoServicioTaller.nombre) == normalized_name.lower(),
            CatalogoServicioTaller.id_catalogo_servicio != exclude_catalog_id
            if exclude_catalog_id is not None
            else True,
        )
    )
    if duplicate_name_in_workshop is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Catalog service name already exists for this workshop.",
        )


def _validate_prequotation_prerequisites(incident: Incidente) -> None:
    if (
        incident.fecha_triaje is None
        or incident.id_especialidad_detectada is None
        or incident.severidad is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident triage is incomplete for technical prequotation.",
        )
    if incident.requiere_revision_manual:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident still requires manual review before technical prequotation.",
        )


def _get_catalog_match_text(incident: Incidente) -> str:
    diagnosis_parts: list[str] = []
    if incident.diagnostico_ia_resumen:
        diagnosis_parts.append(incident.diagnostico_ia_resumen)
    if incident.diagnostico_ia_json:
        diagnosis_parts.append(json.dumps(incident.diagnostico_ia_json, ensure_ascii=False, sort_keys=True))
    return _normalize_catalog_name(" ".join(diagnosis_parts)) or ""


def _select_catalog_service_for_prequotation(
    *,
    db: Session,
    incident: Incidente,
    workshop_id: int,
) -> CatalogoServicioTaller:
    _validate_prequotation_prerequisites(incident)
    catalog_rows = list(
        db.scalars(
            _build_workshop_catalog_query().where(
                CatalogoServicioTaller.id_taller == workshop_id,
                CatalogoServicioTaller.id_especialidad == incident.id_especialidad_detectada,
                CatalogoServicioTaller.activo.is_(True),
            )
        )
    )
    if not catalog_rows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No active catalog service matches the detected specialty for this workshop. "
                "Configure CU26 catalog before accepting the request."
            ),
        )

    diagnosis_text = _get_catalog_match_text(incident)
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


def _estimate_prequotation_complexity(
    *,
    db: Session,
    incident: Incidente,
    workshop_id: int,
    catalog_row: CatalogoServicioTaller,
) -> tuple[Decimal, str, int]:
    base_midpoint = (catalog_row.precio_base_min + catalog_row.precio_base_max) / Decimal("2")
    history_services = list(
        db.scalars(
            select(Servicio)
            .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
            .join(Incidente, Incidente.id_incidente == SolicitudServicio.id_incidente)
            .where(
                SolicitudServicio.id_taller == workshop_id,
                Incidente.id_especialidad_detectada == incident.id_especialidad_detectada,
                Servicio.estado.in_(tuple(PREQUOTATION_HISTORICAL_SERVICE_STATES)),
                or_(
                    Servicio.costo_total.is_not(None),
                    Servicio.costo_mano_obra.is_not(None),
                ),
            )
            .order_by(Servicio.id_servicio.desc())
        )
    )
    historical_costs: list[Decimal] = []
    for service in history_services:
        effective_cost = service.costo_total
        if effective_cost is None or effective_cost <= 0:
            effective_cost = service.costo_mano_obra
        if effective_cost is None or effective_cost <= 0:
            continue
        historical_costs.append(Decimal(effective_cost))

    if historical_costs and base_midpoint > 0:
        average_cost = sum(historical_costs) / Decimal(len(historical_costs))
        factor = average_cost / base_midpoint
        factor = max(PREQUOTATION_MIN_FACTOR, min(PREQUOTATION_MAX_FACTOR, factor))
        return (factor.quantize(Decimal("0.01")), "HISTORICAL", len(historical_costs))

    fallback_factor = PREQUOTATION_SEVERITY_FACTORS.get(
        incident.severidad or "",
        PREQUOTATION_MIN_FACTOR,
    )
    fallback_factor = max(PREQUOTATION_MIN_FACTOR, min(PREQUOTATION_MAX_FACTOR, fallback_factor))
    return (fallback_factor.quantize(Decimal("0.01")), "SEVERITY_FALLBACK", 0)


def _generate_prequotation_code(
    *,
    db: Session,
    service_id: int,
) -> str:
    for attempt in range(3):
        timestamp = utc_now()
        suffix = f"-{attempt}" if attempt else ""
        candidate = f"PRE-{service_id}-{timestamp:%Y%m%d%H%M%S%f}{suffix}"
        exists = db.scalar(
            select(Servicio.id_servicio).where(Servicio.codigo_precotizacion == candidate)
        )
        if exists is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Prequotation code could not be generated uniquely.",
    )


def _build_prequotation_payload(
    *,
    incident: Incidente,
    request_row: SolicitudServicio,
    service: Servicio,
    catalog_row: CatalogoServicioTaller,
    complexity_source: str,
    history_sample_size: int,
    complexity_factor: Decimal,
) -> dict[str, Any]:
    specialty_name = (
        incident.especialidad_detectada.nombre
        if incident.especialidad_detectada is not None
        else None
    )
    return {
        "service_id": service.id_servicio,
        "request_id": request_row.id_solicitud,
        "incident_id": incident.id_incidente,
        "workshop_id": request_row.id_taller,
        "catalog_id": catalog_row.id_catalogo_servicio,
        "catalog_service_name": catalog_row.nombre,
        "detected_specialty_id": incident.id_especialidad_detectada,
        "detected_specialty_name": specialty_name,
        "severity": incident.severidad,
        "complexity_source": complexity_source,
        "history_sample_size": history_sample_size,
        "complexity_factor": str(complexity_factor),
        "codigo_precotizacion": service.codigo_precotizacion,
        "monto_precotizado_min": str(service.monto_precotizado_min),
        "monto_precotizado_max": str(service.monto_precotizado_max),
        "incluye_repuestos_basicos": catalog_row.incluye_repuestos_basicos,
        "currency": PREQUOTATION_CURRENCY,
    }


def _apply_service_prequotation(
    *,
    db: Session,
    incident: Incidente,
    request_row: SolicitudServicio,
    service: Servicio,
    catalog_row: CatalogoServicioTaller | None = None,
) -> tuple[CatalogoServicioTaller, dict[str, Any]]:
    if catalog_row is None:
        catalog_row = _select_catalog_service_for_prequotation(
            db=db,
            incident=incident,
            workshop_id=request_row.id_taller,
        )
    complexity_factor, complexity_source, history_sample_size = _estimate_prequotation_complexity(
        db=db,
        incident=incident,
        workshop_id=request_row.id_taller,
        catalog_row=catalog_row,
    )
    prequotation_min = _quantize_currency(catalog_row.precio_base_min * complexity_factor)
    prequotation_max = _quantize_currency(catalog_row.precio_base_max * complexity_factor)
    if prequotation_max < prequotation_min:
        prequotation_max = prequotation_min
    service.codigo_precotizacion = _generate_prequotation_code(
        db=db,
        service_id=service.id_servicio,
    )
    service.monto_precotizado_min = prequotation_min
    service.monto_precotizado_max = prequotation_max
    service.costo_mano_obra = _quantize_currency((prequotation_min + prequotation_max) / Decimal("2"))
    payload = _build_prequotation_payload(
        incident=incident,
        request_row=request_row,
        service=service,
        catalog_row=catalog_row,
        complexity_source=complexity_source,
        history_sample_size=history_sample_size,
        complexity_factor=complexity_factor,
    )
    return catalog_row, payload


def _build_specialty_summary(specialty: Especialidad | None) -> SpecialtySummaryResponse | None:
    if specialty is None:
        return None
    return SpecialtySummaryResponse(
        id_especialidad=specialty.id_especialidad,
        nombre=specialty.nombre,
    )


def _build_workshop_summary(request_row: SolicitudServicio) -> WorkshopSummaryResponse:
    return WorkshopSummaryResponse(
        id_taller=request_row.taller.id_taller,
        nombre_comercial=request_row.taller.nombre_comercial,
    )


def _build_workshop_summary_from_service(service: Servicio) -> WorkshopSummaryResponse:
    return WorkshopSummaryResponse(
        id_taller=service.solicitud.taller.id_taller,
        nombre_comercial=service.solicitud.taller.nombre_comercial,
    )


def _build_distance_km(request_row: SolicitudServicio) -> Decimal:
    candidate = build_ranked_candidate(
        incident_lat=request_row.incidente.latitud,
        incident_lon=request_row.incidente.longitud,
        taller=request_row.taller,
        used_insurance_priority=request_row.prioridad_seguro,
    )
    return candidate.distance_km


def _create_bitacora_event(
    *,
    admin_user: Usuario,
    incident: Incidente,
    request_row: SolicitudServicio,
    accion: str,
    descripcion: str,
    datos_nuevos: dict[str, Any] | None,
    ip_origen: str | None,
    user_agent: str | None,
    id_servicio: int | None = None,
) -> Bitacora:
    entidad_principal = "SERVICIO" if id_servicio is not None else "SOLICITUD"
    id_entidad = id_servicio if id_servicio is not None else request_row.id_solicitud
    return Bitacora(
        accion=accion,
        tipo_evento="OPERACION_TALLER",
        descripcion=descripcion,
        entidad_principal=entidad_principal,
        id_entidad_principal=id_entidad,
        datos_nuevos=datos_nuevos,
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=admin_user.id_usuario,
        id_incidente=incident.id_incidente,
        id_solicitud=request_row.id_solicitud,
        id_servicio=id_servicio,
    )


def _get_client_user(db: Session, *, cliente_id: int) -> Usuario:
    client_user = db.scalar(
        select(Usuario).where(Usuario.id_persona == cliente_id)
    )
    if client_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Incident client account is not provisioned.",
        )
    return client_user


def _get_operario_user(db: Session, *, operario_id: int) -> Usuario:
    operario_user = db.scalar(select(Usuario).where(Usuario.id_persona == operario_id))
    if operario_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assigned operario account is not provisioned.",
        )
    return operario_user


def _create_client_notification(
    *,
    db: Session,
    client_user: Usuario,
    request_row: SolicitudServicio,
    title: str,
    message: str,
    payload: dict[str, Any],
    service_id: int | None = None,
) -> None:
    db.add(
        Notificacion(
            id_usuario=client_user.id_usuario,
            id_solicitud=request_row.id_solicitud,
            id_servicio=service_id,
            canal="WEB",
            titulo=title,
            mensaje=message,
            payload=payload,
            estado="PENDIENTE",
        )
    )


def _create_operario_notification(
    *,
    db: Session,
    operario_user: Usuario,
    service: Servicio,
    title: str,
    message: str,
    payload: dict[str, Any],
) -> None:
    db.add(
        Notificacion(
            id_usuario=operario_user.id_usuario,
            id_solicitud=service.id_solicitud,
            id_servicio=service.id_servicio,
            canal="WEB",
            titulo=title,
            mensaje=message,
            payload=payload,
            estado="PENDIENTE",
        )
    )


def _create_service_notification(
    *,
    db: Session,
    user: Usuario,
    service: Servicio,
    title: str,
    message: str,
    payload: dict[str, Any],
) -> None:
    db.add(
        Notificacion(
            id_usuario=user.id_usuario,
            id_solicitud=service.id_solicitud,
            id_servicio=service.id_servicio,
            canal="WEB",
            titulo=title,
            mensaje=message,
            payload=payload,
            estado="PENDIENTE",
        )
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


def _normalize_expired_request(
    *,
    db: Session,
    request_row: SolicitudServicio,
    admin_context: WorkshopAdminContext,
    ip_origen: str | None,
    user_agent: str | None,
    now,
) -> bool:
    if request_row.estado != "PENDIENTE" or request_row.fecha_expiracion > now:
        return False

    request_row.estado = "EXPIRADA"
    request_row.es_actual = False
    request_row.fecha_respuesta = now
    request_row.motivo_cierre = "Tiempo de respuesta agotado."
    request_row.incidente.estado = "DIAGNOSTICADO"
    db.add(
        _create_bitacora_event(
            admin_user=admin_context.user,
            incident=request_row.incidente,
            request_row=request_row,
            accion="SOLICITUD_EXPIRADA",
            descripcion="La solicitud expiro antes de la decision del taller.",
            datos_nuevos={
                "id_taller": request_row.id_taller,
                "estado": "EXPIRADA",
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    return True


def _get_workshop_request(
    *,
    db: Session,
    request_id: int,
    workshop_id: int,
) -> SolicitudServicio:
    request_row = db.scalar(
        _build_request_query().where(
            SolicitudServicio.id_solicitud == request_id,
            SolicitudServicio.id_taller == workshop_id,
        )
    )
    if request_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop request not found.",
        )
    return request_row


def _get_workshop_service(
    *,
    db: Session,
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


def _validate_service_assignment_eligible(service: Servicio) -> Incidente:
    incident = service.solicitud.incidente
    if service.solicitud.estado != "ACEPTADA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service request is not accepted for operario assignment.",
        )
    if service.id_persona_operario is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service already has an operario assigned.",
        )
    if service.estado not in ELIGIBLE_PRE_ASSIGNMENT_SERVICE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not waiting for operario assignment.",
        )
    if (
        incident.id_especialidad_detectada is None
        or incident.severidad is None
        or incident.fecha_triaje is None
        or incident.requiere_revision_manual
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident is not ready for operario assignment.",
        )
    return incident


def _get_matching_specialty_association(
    operario: Operario,
    *,
    specialty_id: int,
) -> OperarioEspecialidad | None:
    for association in operario.especialidades:
        if association.id_especialidad == specialty_id:
            return association
    return None


def _build_operario_candidate_summary(
    operario: Operario,
    *,
    matched_specialty: OperarioEspecialidad,
) -> OperarioCandidateSummary:
    return OperarioCandidateSummary(
        id_persona_operario=operario.id_persona,
        nombre_completo=f"{operario.persona.nombre} {operario.persona.apellido}",
        estado_disponibilidad=operario.estado_disponibilidad,
        matched_specialty=SpecialtySummaryResponse(
            id_especialidad=matched_specialty.especialidad.id_especialidad,
            nombre=matched_specialty.especialidad.nombre,
        ),
        anios_experiencia=matched_specialty.anios_experiencia,
        certificacion_url=matched_specialty.certificacion_url,
        recommended=True,
        match_reason="Operario del mismo taller con especialidad detectada y disponibilidad vigente.",
    )


def _build_assigned_operario_summary(
    operario: Operario,
    *,
    matched_specialty: OperarioEspecialidad,
) -> AssignedOperarioSummary:
    return AssignedOperarioSummary(
        id_persona_operario=operario.id_persona,
        nombre_completo=f"{operario.persona.nombre} {operario.persona.apellido}",
        estado_disponibilidad=operario.estado_disponibilidad,
        matched_specialty=SpecialtySummaryResponse(
            id_especialidad=matched_specialty.especialidad.id_especialidad,
            nombre=matched_specialty.especialidad.nombre,
        ),
    )


def _get_assigned_operario_service(
    *,
    db: Session,
    service_id: int,
    operario_id: int,
) -> Servicio:
    service = db.scalar(
        _build_repair_service_query().where(
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


def _validate_repair_report_eligible(service: Servicio) -> Incidente:
    if service.estado not in REPAIR_REPORT_SAVE_ALLOWED_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not in a repair-compatible state for the repair report.",
        )
    return service.solicitud.incidente


def _validate_final_images(final_images: list[UploadFile]) -> None:
    for image in final_images:
        content_type = image.content_type or ""
        if not content_type.startswith(IMAGE_MIME_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid final evidence image type.",
            )


def _encode_report_notes(
    *,
    observaciones: str | None,
    recomendaciones: str | None,
) -> str | None:
    if observaciones is None and recomendaciones is None:
        return None
    return json.dumps(
        {
            "v": REPORT_NOTES_VERSION,
            "observaciones": observaciones,
            "recomendaciones": recomendaciones,
        },
        ensure_ascii=False,
    )


def _decode_report_notes(raw_value: str | None) -> tuple[str | None, str | None]:
    if raw_value is None:
        return None, None
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value, None
    if not isinstance(payload, dict):
        return raw_value, None
    return payload.get("observaciones"), payload.get("recomendaciones")


def _serialize_used_spare_part(item: ServicioRepuesto) -> UsedSparePartResponse:
    subtotal = (Decimal(item.cantidad) * Decimal(item.costo_unitario)).quantize(Decimal("0.01"))
    return UsedSparePartResponse(
        id_servicio_repuesto=item.id_servicio_repuesto,
        descripcion=item.descripcion,
        cantidad=Decimal(item.cantidad),
        costo_unitario=Decimal(item.costo_unitario),
        subtotal=subtotal,
        observacion=None,
    )


def _serialize_final_evidence(item: Evidencia) -> FinalEvidenceResponse:
    return FinalEvidenceResponse(
        id_evidencia=item.id_evidencia,
        tipo_evidencia=item.tipo_evidencia,
        categoria=item.categoria,
        url_archivo=item.url_archivo,
        mime_type=item.mime_type,
        tamano_bytes=item.tamano_bytes,
        fecha_registro=item.fecha_registro,
    )


def _get_final_service_evidences(service: Servicio) -> list[Evidencia]:
    return sorted(
        [
            evidence
            for evidence in service.evidencias
            if evidence.id_servicio == service.id_servicio
            and evidence.tipo_evidencia == "IMAGEN"
            and evidence.categoria == "CIERRE"
        ],
        key=lambda item: item.id_evidencia,
    )


def _build_repair_snapshot(service: Servicio) -> RepairReportSnapshotResponse:
    observaciones, recomendaciones = _decode_report_notes(
        service.informe.observaciones if service.informe is not None else None
    )
    used_items = [_serialize_used_spare_part(item) for item in sorted(service.repuestos, key=lambda row: row.id_servicio_repuesto)]
    final_evidences = [_serialize_final_evidence(item) for item in _get_final_service_evidences(service)]
    saved_at = None
    if service.informe is not None:
        saved_at = service.informe.updated_at or service.informe.fecha_registro
    return RepairReportSnapshotResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=service.solicitud.incidente.id_incidente,
        report_id=service.informe.id_informe if service.informe is not None else None,
        accion_realizada=service.informe.accion_realizada if service.informe is not None else None,
        diagnostico_fisico=service.informe.diagnostico_fisico if service.informe is not None else None,
        observaciones=observaciones,
        recomendaciones=recomendaciones,
        total_additional_cost=Decimal(service.costo_repuestos),
        used_items=used_items,
        final_evidences=final_evidences,
        saved_at=saved_at,
    )


def list_workshop_staff(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> list[WorkshopStaffSummary]:
    operarios = list(
        db.execute(
            _build_operario_query()
            .where(Operario.id_taller == admin_context.workshop_id)
            .order_by(Operario.created_at.desc(), Operario.id_persona.desc())
        )
        .unique()
        .scalars()
    )
    return [_build_workshop_staff_summary(item) for item in operarios]


def get_workshop_profile(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> WorkshopProfileResponse:
    taller = _get_admin_workshop(db=db, workshop_id=admin_context.workshop_id)
    return _build_workshop_profile_response(taller)


def list_workshop_catalog_services(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
    include_inactive: bool = False,
) -> list[WorkshopCatalogServiceResponse]:
    query = _build_workshop_catalog_query().where(
        CatalogoServicioTaller.id_taller == admin_context.workshop_id,
    )
    if not include_inactive:
        query = query.where(CatalogoServicioTaller.activo.is_(True))
    catalog_rows = list(
        db.scalars(
            query.order_by(
                CatalogoServicioTaller.activo.desc(),
                func.lower(CatalogoServicioTaller.nombre),
                CatalogoServicioTaller.id_catalogo_servicio.desc(),
            )
        )
    )
    return [_serialize_workshop_catalog_service(item) for item in catalog_rows]


def create_workshop_catalog_service(
    *,
    payload: WorkshopCatalogServiceCreateRequest,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopCatalogServiceResponse:
    normalized_name = _normalize_text(payload.nombre)
    specialty = _ensure_catalog_specialty_exists(
        db=db,
        specialty_id=payload.id_especialidad,
    )
    _ensure_catalog_duplicate_rules(
        db=db,
        workshop_id=admin_context.workshop_id,
        specialty_id=payload.id_especialidad,
        normalized_name=normalized_name,
    )

    catalog_row = CatalogoServicioTaller(
        id_taller=admin_context.workshop_id,
        id_especialidad=payload.id_especialidad,
        nombre=normalized_name,
        descripcion=_normalize_optional_text(payload.descripcion),
        precio_base_min=payload.precio_base_min,
        precio_base_max=payload.precio_base_max,
        incluye_repuestos_basicos=payload.incluye_repuestos_basicos,
        activo=True,
    )
    catalog_row.especialidad = specialty
    db.add(catalog_row)
    db.flush()
    db.add(
        _create_workshop_catalog_bitacora_event(
            admin_context=admin_context,
            accion="CATALOGO_SERVICIO_TALLER_CREADO",
            descripcion="El administrador registro un servicio base en el catalogo del taller.",
            datos_originales=None,
            datos_nuevos={
                "workshop_id": admin_context.workshop_id,
                "catalog_id": catalog_row.id_catalogo_servicio,
                "id_especialidad": catalog_row.id_especialidad,
                "nombre": catalog_row.nombre,
                "precio_base_min": str(catalog_row.precio_base_min),
                "precio_base_max": str(catalog_row.precio_base_max),
                "incluye_repuestos_basicos": catalog_row.incluye_repuestos_basicos,
                "activo": catalog_row.activo,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Catalog service conflicts with existing workshop data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Catalog service could not be created.",
        ) from exc

    db.expire_all()
    refreshed = _get_workshop_catalog_service(
        db=db,
        catalog_id=catalog_row.id_catalogo_servicio,
        workshop_id=admin_context.workshop_id,
    )
    return _serialize_workshop_catalog_service(refreshed)


def update_workshop_catalog_service(
    *,
    catalog_id: int,
    payload: WorkshopCatalogServiceUpdateRequest,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopCatalogServiceResponse:
    catalog_row = _get_workshop_catalog_service(
        db=db,
        catalog_id=catalog_id,
        workshop_id=admin_context.workshop_id,
    )
    previous_payload = {
        "id_especialidad": catalog_row.id_especialidad,
        "nombre": catalog_row.nombre,
        "descripcion": catalog_row.descripcion,
        "precio_base_min": str(catalog_row.precio_base_min),
        "precio_base_max": str(catalog_row.precio_base_max),
        "incluye_repuestos_basicos": catalog_row.incluye_repuestos_basicos,
        "activo": catalog_row.activo,
    }

    target_specialty_id = (
        payload.id_especialidad
        if payload.id_especialidad is not None
        else catalog_row.id_especialidad
    )
    target_name = (
        _normalize_text(payload.nombre)
        if payload.nombre is not None
        else catalog_row.nombre
    )
    target_min = (
        payload.precio_base_min
        if payload.precio_base_min is not None
        else catalog_row.precio_base_min
    )
    target_max = (
        payload.precio_base_max
        if payload.precio_base_max is not None
        else catalog_row.precio_base_max
    )
    if target_max < target_min:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="precio_base_max must be greater than or equal to precio_base_min.",
        )

    specialty = _ensure_catalog_specialty_exists(
        db=db,
        specialty_id=target_specialty_id,
    )
    _ensure_catalog_duplicate_rules(
        db=db,
        workshop_id=admin_context.workshop_id,
        specialty_id=target_specialty_id,
        normalized_name=target_name,
        exclude_catalog_id=catalog_row.id_catalogo_servicio,
    )

    catalog_row.id_especialidad = target_specialty_id
    catalog_row.nombre = target_name
    if payload.descripcion is not None:
        catalog_row.descripcion = _normalize_optional_text(payload.descripcion)
    catalog_row.precio_base_min = target_min
    catalog_row.precio_base_max = target_max
    if payload.incluye_repuestos_basicos is not None:
        catalog_row.incluye_repuestos_basicos = payload.incluye_repuestos_basicos
    if payload.activo is not None:
        catalog_row.activo = payload.activo
    catalog_row.especialidad = specialty

    db.add(
        _create_workshop_catalog_bitacora_event(
            admin_context=admin_context,
            accion="CATALOGO_SERVICIO_TALLER_ACTUALIZADO",
            descripcion="El administrador actualizo un servicio del catalogo del taller.",
            datos_originales=previous_payload,
            datos_nuevos={
                "workshop_id": admin_context.workshop_id,
                "catalog_id": catalog_row.id_catalogo_servicio,
                "id_especialidad": catalog_row.id_especialidad,
                "nombre": catalog_row.nombre,
                "descripcion": catalog_row.descripcion,
                "precio_base_min": str(catalog_row.precio_base_min),
                "precio_base_max": str(catalog_row.precio_base_max),
                "incluye_repuestos_basicos": catalog_row.incluye_repuestos_basicos,
                "activo": catalog_row.activo,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Catalog service conflicts with existing workshop data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Catalog service could not be updated.",
        ) from exc

    db.expire_all()
    refreshed = _get_workshop_catalog_service(
        db=db,
        catalog_id=catalog_row.id_catalogo_servicio,
        workshop_id=admin_context.workshop_id,
    )
    return _serialize_workshop_catalog_service(refreshed)


def deactivate_workshop_catalog_service(
    *,
    catalog_id: int,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopCatalogServiceResponse:
    catalog_row = _get_workshop_catalog_service(
        db=db,
        catalog_id=catalog_id,
        workshop_id=admin_context.workshop_id,
    )
    if not catalog_row.activo:
        return _serialize_workshop_catalog_service(catalog_row)

    previous_payload = {
        "activo": catalog_row.activo,
        "nombre": catalog_row.nombre,
        "id_especialidad": catalog_row.id_especialidad,
    }
    catalog_row.activo = False
    db.add(
        _create_workshop_catalog_bitacora_event(
            admin_context=admin_context,
            accion="CATALOGO_SERVICIO_TALLER_DESACTIVADO",
            descripcion="El administrador desactivo un servicio del catalogo del taller.",
            datos_originales=previous_payload,
            datos_nuevos={
                "workshop_id": admin_context.workshop_id,
                "catalog_id": catalog_row.id_catalogo_servicio,
                "id_especialidad": catalog_row.id_especialidad,
                "nombre": catalog_row.nombre,
                "precio_base_min": str(catalog_row.precio_base_min),
                "precio_base_max": str(catalog_row.precio_base_max),
                "incluye_repuestos_basicos": catalog_row.incluye_repuestos_basicos,
                "activo": catalog_row.activo,
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
            detail="Catalog service could not be deactivated.",
        ) from exc

    db.expire_all()
    refreshed = _get_workshop_catalog_service(
        db=db,
        catalog_id=catalog_row.id_catalogo_servicio,
        workshop_id=admin_context.workshop_id,
    )
    return _serialize_workshop_catalog_service(refreshed)


def list_workshop_media_files(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> list[WorkshopMediaFileResponse]:
    taller = _get_admin_workshop(db=db, workshop_id=admin_context.workshop_id)
    active_files = sorted(
        [item for item in taller.archivos if item.activo],
        key=lambda item: (item.fecha_registro, item.id_taller_archivo),
        reverse=True,
    )
    return [_serialize_workshop_media_file(item) for item in active_files]


def upload_workshop_media_file(
    *,
    payload: WorkshopMediaUploadRequest,
    file: UploadFile,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopMediaFileResponse:
    taller = _get_admin_workshop(db=db, workshop_id=admin_context.workshop_id)
    _validate_workshop_media_upload(tipo_archivo=payload.tipo_archivo, file=file)

    folder = "imagenes" if payload.tipo_archivo == "IMAGEN_TALLER" else "certificados"
    storage = get_triage_storage()
    stored_media: StoredMedia | None = None

    try:
        stored_media = storage.save_workshop_file(
            workshop_id=taller.id_taller,
            folder=folder,
            upload=file,
        )
        file_row = TallerArchivo(
            id_taller=taller.id_taller,
            tipo_archivo=payload.tipo_archivo,
            nombre_archivo=file.filename or stored_media.absolute_path.name,
            url_archivo=stored_media.locator,
            mime_type=stored_media.mime_type,
            tamano_bytes=stored_media.size_bytes,
            descripcion=_normalize_optional_text(payload.descripcion),
            activo=True,
        )
        db.add(file_row)
        db.flush()
        db.add(
            _create_workshop_media_bitacora(
                admin_context=admin_context,
                accion="TALLER_ARCHIVO_SUBIDO",
                descripcion="El administrador subio un archivo del perfil del taller.",
                taller=taller,
                file_row=file_row,
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )
        db.commit()
    except HTTPException:
        db.rollback()
        if stored_media is not None:
            storage.delete_many([stored_media])
        raise
    except StorageError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workshop media file could not be stored.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        if stored_media is not None:
            storage.delete_many([stored_media])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workshop media file could not be persisted.",
        ) from exc

    db.expire_all()
    db.refresh(file_row)
    return _serialize_workshop_media_file(file_row)


def deactivate_workshop_media_file(
    *,
    file_id: int,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopMediaFileResponse:
    taller = _get_admin_workshop(db=db, workshop_id=admin_context.workshop_id)
    file_row = _get_workshop_media_file(
        db=db,
        file_id=file_id,
        workshop_id=admin_context.workshop_id,
    )
    if not file_row.activo:
        return _serialize_workshop_media_file(file_row)

    file_row.activo = False
    db.add(
        _create_workshop_media_bitacora(
            admin_context=admin_context,
            accion="TALLER_ARCHIVO_DESACTIVADO",
            descripcion="El administrador desactivo un archivo del perfil del taller.",
            taller=taller,
            file_row=file_row,
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
            detail="Workshop media file could not be deactivated.",
        ) from exc

    db.expire_all()
    return _serialize_workshop_media_file(file_row)


def update_workshop_profile(
    *,
    payload: WorkshopProfileUpdateRequest,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopProfileResponse:
    specialty_ids = payload.specialty_ids
    if len(specialty_ids) != len(set(specialty_ids)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Specialty ids must be unique inside the request.",
        )

    taller = _get_admin_workshop(db=db, workshop_id=admin_context.workshop_id)
    _get_workshop_specialties_by_ids(db, specialty_ids=specialty_ids)

    previous_payload = {
        "nombre_comercial": taller.nombre_comercial,
        "descripcion": taller.descripcion,
        "latitud": str(taller.latitud),
        "longitud": str(taller.longitud),
        "radio_accion_km": str(taller.radio_accion_km),
        "acepta_seguro_propio": taller.acepta_seguro_propio,
        "specialty_ids": sorted(
            association.id_especialidad
            for association in taller.especialidades
            if association.activo
        ),
    }

    taller.nombre_comercial = _normalize_text(payload.nombre_comercial)
    taller.descripcion = _normalize_optional_text(payload.descripcion)
    taller.latitud = payload.latitud
    taller.longitud = payload.longitud
    taller.radio_accion_km = payload.radio_accion_km
    if payload.acepta_seguro_propio is not None:
        taller.acepta_seguro_propio = payload.acepta_seguro_propio

    current_by_specialty_id = {
        association.id_especialidad: association for association in taller.especialidades
    }
    requested_ids = set(specialty_ids)
    for association in list(taller.especialidades):
        if association.id_especialidad not in requested_ids:
            db.delete(association)

    for specialty_id in specialty_ids:
        association = current_by_specialty_id.get(specialty_id)
        if association is None:
            db.add(
                TallerEspecialidad(
                    id_taller=taller.id_taller,
                    id_especialidad=specialty_id,
                    activo=True,
                )
            )
        else:
            association.activo = True

    db.add(
        _create_workshop_profile_bitacora_event(
            admin_context=admin_context,
            taller=taller,
            datos_nuevos={
                "workshop_id": taller.id_taller,
                "previous": previous_payload,
                "updated_specialty_ids": sorted(specialty_ids),
                "changed_fields": [
                    field_name
                    for field_name, previous_value, new_value in (
                        ("nombre_comercial", previous_payload["nombre_comercial"], taller.nombre_comercial),
                        ("descripcion", previous_payload["descripcion"], taller.descripcion),
                        ("latitud", previous_payload["latitud"], str(taller.latitud)),
                        ("longitud", previous_payload["longitud"], str(taller.longitud)),
                        ("radio_accion_km", previous_payload["radio_accion_km"], str(taller.radio_accion_km)),
                        (
                            "acepta_seguro_propio",
                            previous_payload["acepta_seguro_propio"],
                            taller.acepta_seguro_propio,
                        ),
                        ("specialty_ids", previous_payload["specialty_ids"], sorted(specialty_ids)),
                    )
                    if previous_value != new_value
                ],
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workshop profile conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workshop profile could not be updated.",
        ) from exc

    db.expire_all()
    refreshed_taller = _get_admin_workshop(db=db, workshop_id=admin_context.workshop_id)
    return _build_workshop_profile_response(refreshed_taller)


def register_workshop_operario(
    *,
    payload: WorkshopStaffCreateRequest,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopStaffSummary:
    if not payload.specialties:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one specialty is required for a new operario.",
        )

    specialty_ids = [item.id_especialidad for item in payload.specialties]
    if len(specialty_ids) != len(set(specialty_ids)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Specialty ids must be unique inside the request.",
        )

    _ensure_staff_email_unique(db, payload.email)
    _ensure_staff_ci_unique(db, payload.ci)
    _ensure_staff_phone_unique(db, payload.telefono)
    specialty_map = _get_specialties_by_ids(db, specialty_ids=specialty_ids)

    persona = Persona(
        nombre=_normalize_text(payload.nombre),
        apellido=_normalize_text(payload.apellido),
        ci=_normalize_text(payload.ci),
        telefono=_normalize_phone(payload.telefono),
        direccion=_normalize_optional_text(payload.direccion),
    )
    db.add(persona)
    db.flush()

    usuario = Usuario(
        id_persona=persona.id_persona,
        email=_normalize_email(payload.email),
        password_hash=hash_password(payload.password),
        tipo_usuario="OPERARIO",
        activo=True,
        intentos=0,
        bloqueado=False,
    )
    operario = Operario(
        id_persona=persona.id_persona,
        id_taller=admin_context.workshop_id,
        estado_disponibilidad="DISPONIBLE",
        activo=True,
    )
    db.add(usuario)
    db.add(operario)

    for item in payload.specialties:
        db.add(
            OperarioEspecialidad(
                id_persona=persona.id_persona,
                id_especialidad=item.id_especialidad,
                anios_experiencia=item.anios_experiencia,
                certificacion_url=_normalize_optional_text(item.certificacion_url),
            )
        )

    db.add(
        _create_staff_bitacora_event(
            admin_context=admin_context,
            accion="OPERARIO_REGISTRADO",
            descripcion="El administrador registro un nuevo operario para su taller.",
            target_user_id=None,
            target_operario_id=persona.id_persona,
            datos_nuevos={
                "workshop_id": admin_context.workshop_id,
                "operario_id": persona.id_persona,
                "estado_disponibilidad": "DISPONIBLE",
                "specialties": [
                    {
                        "id_especialidad": item.id_especialidad,
                        "nombre": specialty_map[item.id_especialidad].nombre,
                    }
                    for item in payload.specialties
                ],
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operario conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Operario could not be created.",
        ) from exc

    created_operario = _get_workshop_operario(
        db=db,
        operario_id=persona.id_persona,
        workshop_id=admin_context.workshop_id,
    )
    return _build_workshop_staff_summary(created_operario)


def update_workshop_operario_availability(
    *,
    operario_id: int,
    payload: WorkshopStaffAvailabilityUpdateRequest,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopStaffSummary:
    if payload.new_status not in OPERARIO_AVAILABILITY_ALLOWED_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operario availability status is not supported.",
        )

    operario = _get_workshop_operario(
        db=db,
        operario_id=operario_id,
        workshop_id=admin_context.workshop_id,
    )
    previous_status = operario.estado_disponibilidad
    if previous_status == payload.new_status:
        return _build_workshop_staff_summary(operario)

    operario.estado_disponibilidad = payload.new_status
    if payload.new_status == "BAJA":
        operario.activo = False
    elif not operario.activo:
        operario.activo = True

    usuario = operario.persona.usuario
    db.add(
        _create_staff_bitacora_event(
            admin_context=admin_context,
            accion="OPERARIO_DISPONIBILIDAD_ACTUALIZADA",
            descripcion="El administrador actualizo la disponibilidad operativa de un funcionario.",
            target_user_id=usuario.id_usuario if usuario is not None else None,
            target_operario_id=operario.id_persona,
            datos_nuevos={
                "workshop_id": admin_context.workshop_id,
                "operario_id": operario.id_persona,
                "previous_status": previous_status,
                "new_status": payload.new_status,
                "reason": _normalize_optional_text(payload.reason),
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
            detail="Operario availability could not be updated.",
        ) from exc

    updated_operario = _get_workshop_operario(
        db=db,
        operario_id=operario_id,
        workshop_id=admin_context.workshop_id,
    )
    return _build_workshop_staff_summary(updated_operario)


def _serialize_request_summary(request_row: SolicitudServicio) -> WorkshopRequestSummary:
    return WorkshopRequestSummary(
        request_id=request_row.id_solicitud,
        incident_id=request_row.id_incidente,
        incident_state=request_row.incidente.estado,
        sent_at=request_row.fecha_envio,
        expires_at=request_row.fecha_expiracion,
        distance_km=_build_distance_km(request_row),
        detected_specialty=_build_specialty_summary(request_row.incidente.especialidad_detectada),
        severity=request_row.incidente.severidad,
        ai_summary=request_row.incidente.diagnostico_ia_resumen,
        used_insurance_priority=request_row.prioridad_seguro,
        attempt_number=request_row.intento_numero,
        score_total=request_row.score_total,
        request_status=request_row.estado,
    )


def _serialize_request_detail(
    request_row: SolicitudServicio,
    *,
    is_expired: bool,
    db: Session,
) -> WorkshopRequestDetailResponse:
    service = request_row.servicio
    return WorkshopRequestDetailResponse(
        request_id=request_row.id_solicitud,
        request_status=request_row.estado,
        incident_id=request_row.id_incidente,
        incident_state=request_row.incidente.estado,
        workshop=_build_workshop_summary(request_row),
        sent_at=request_row.fecha_envio,
        expires_at=request_row.fecha_expiracion,
        is_expired=is_expired,
        distance_km=_build_distance_km(request_row),
        used_insurance_priority=request_row.prioridad_seguro,
        attempt_number=request_row.intento_numero,
        score_proximidad=request_row.score_proximidad,
        score_reputacion=request_row.score_reputacion,
        score_total=request_row.score_total,
        incident_latitud=request_row.incidente.latitud,
        incident_longitud=request_row.incidente.longitud,
        client_reported_specialty=_build_specialty_summary(
            request_row.incidente.especialidad_reportada_cliente
        ),
        detected_specialty=_build_specialty_summary(request_row.incidente.especialidad_detectada),
        severity=request_row.incidente.severidad,
        ai_summary=request_row.incidente.diagnostico_ia_resumen,
        transcripcion_audio=request_row.incidente.transcripcion_audio,
        image_labels=request_row.incidente.etiquetas_imagen,
        service_id=service.id_servicio if service is not None else None,
        service_state=service.estado if service is not None else None,
        prequotation_code=service.codigo_precotizacion if service is not None else None,
        prequotation_min=service.monto_precotizado_min if service is not None else None,
        prequotation_max=service.monto_precotizado_max if service is not None else None,
        prequotation_currency=(
            PREQUOTATION_CURRENCY
            if service is not None and service.codigo_precotizacion is not None
            else None
        ),
        catalog_service_name=_get_catalog_service_name_from_prequotation(db=db, service=service),
        motivo_cierre=request_row.motivo_cierre,
    )


def list_pending_workshop_requests(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> list[WorkshopRequestSummary]:
    pending_requests = list(
        db.scalars(
            _build_request_query()
            .where(
                SolicitudServicio.id_taller == admin_context.workshop_id,
                SolicitudServicio.estado == "PENDIENTE",
                SolicitudServicio.es_actual.is_(True),
            )
            .order_by(SolicitudServicio.fecha_expiracion.asc(), SolicitudServicio.fecha_envio.desc())
        )
    )

    now = utc_now()
    expired_changed = False
    for request_row in pending_requests:
        expired_changed = _normalize_expired_request(
            db=db,
            request_row=request_row,
            admin_context=admin_context,
            ip_origen=None,
            user_agent=None,
            now=now,
        ) or expired_changed

    if expired_changed:
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workshop requests could not be normalized.",
            ) from exc
        pending_requests = list(
            db.scalars(
                _build_request_query()
                .where(
                    SolicitudServicio.id_taller == admin_context.workshop_id,
                    SolicitudServicio.estado == "PENDIENTE",
                    SolicitudServicio.es_actual.is_(True),
                )
                .order_by(
                    SolicitudServicio.fecha_expiracion.asc(),
                    SolicitudServicio.fecha_envio.desc(),
                )
            )
        )

    return [_serialize_request_summary(item) for item in pending_requests]


def get_workshop_request_detail(
    *,
    request_id: int,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> WorkshopRequestDetailResponse:
    request_row = _get_workshop_request(
        db=db,
        request_id=request_id,
        workshop_id=admin_context.workshop_id,
    )
    now = utc_now()
    was_expired = _normalize_expired_request(
        db=db,
        request_row=request_row,
        admin_context=admin_context,
        ip_origen=None,
        user_agent=None,
        now=now,
    )
    if was_expired:
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workshop request expiration could not be persisted.",
            ) from exc
        request_row = _get_workshop_request(
            db=db,
            request_id=request_id,
            workshop_id=admin_context.workshop_id,
        )

    is_expired = request_row.estado == "EXPIRADA"
    return _serialize_request_detail(request_row, is_expired=is_expired, db=db)


def list_waiting_assignment_services(
    *,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> list[WaitingAssignmentServiceSummary]:
    services = list(
        db.scalars(
            _build_service_query()
            .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
            .where(
                SolicitudServicio.id_taller == admin_context.workshop_id,
                SolicitudServicio.estado == "ACEPTADA",
                Servicio.id_persona_operario.is_(None),
                Servicio.estado == WAITING_ASSIGNMENT_SERVICE_STATE,
            )
            .order_by(Servicio.fecha_asignacion_operario.desc().nullslast(), Servicio.id_servicio.desc())
        )
    )
    return [
        WaitingAssignmentServiceSummary(
            service_id=service.id_servicio,
            service_state=service.estado,
            incident_id=service.solicitud.incidente.id_incidente,
            incident_state=service.solicitud.incidente.estado,
            request_id=service.id_solicitud,
            workshop=_build_workshop_summary_from_service(service),
            detected_specialty=_build_specialty_summary(
                service.solicitud.incidente.especialidad_detectada
            ),
            severity=service.solicitud.incidente.severidad,
            ai_summary=service.solicitud.incidente.diagnostico_ia_resumen,
            prequotation_code=service.codigo_precotizacion,
            prequotation_min=service.monto_precotizado_min,
            prequotation_max=service.monto_precotizado_max,
            prequotation_currency=(
                PREQUOTATION_CURRENCY if service.codigo_precotizacion is not None else None
            ),
            catalog_service_name=_get_catalog_service_name_from_prequotation(
                db=db,
                service=service,
            ),
            assignment_timestamp=service.fecha_asignacion_operario,
        )
        for service in services
    ]


def get_operario_candidates_for_service(
    *,
    service_id: int,
    admin_context: WorkshopAdminContext,
    db: Session,
) -> list[OperarioCandidateSummary]:
    service = _get_workshop_service(
        db=db,
        service_id=service_id,
        workshop_id=admin_context.workshop_id,
    )
    incident = _validate_service_assignment_eligible(service)

    operarios = list(
        db.execute(
            _build_operario_query().where(
                Operario.id_taller == admin_context.workshop_id,
                Operario.activo.is_(True),
                Operario.estado_disponibilidad.in_(AVAILABLE_OPERARIO_STATES),
            )
        )
        .unique()
        .scalars()
    )

    candidates: list[tuple[Operario, OperarioEspecialidad]] = []
    for operario in operarios:
        matched_specialty = _get_matching_specialty_association(
            operario,
            specialty_id=incident.id_especialidad_detectada,
        )
        if matched_specialty is not None:
            candidates.append((operario, matched_specialty))

    ordered = sorted(
        candidates,
        key=lambda item: (
            -item[1].anios_experiencia,
            item[0].id_persona,
        ),
    )
    return [
        _build_operario_candidate_summary(operario, matched_specialty=matched_specialty)
        for operario, matched_specialty in ordered
    ]


def get_repair_report_snapshot(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> RepairReportSnapshotResponse:
    service = _get_assigned_operario_service(
        db=db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    _validate_repair_report_eligible(service)
    return _build_repair_snapshot(service)


def save_repair_report(
    *,
    service_id: int,
    accion_realizada: str,
    diagnostico_fisico: str | None,
    observaciones: str | None,
    recomendaciones: str | None,
    used_items: list[RepairReportItemInput],
    final_images: list[UploadFile],
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> RepairReportSaveResponse:
    service = _get_assigned_operario_service(
        db=db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    incident = _validate_repair_report_eligible(service)
    _validate_final_images(final_images)

    storage = get_triage_storage()
    stored_media: list[StoredMedia] = []
    previous_state = service.estado

    try:
        total_additional_cost = Decimal("0.00")
        for item in used_items:
            subtotal = (Decimal(item.cantidad) * Decimal(item.costo_unitario)).quantize(
                Decimal("0.01")
            )
            total_additional_cost += subtotal

        report = service.informe
        encoded_notes = _encode_report_notes(
            observaciones=observaciones,
            recomendaciones=recomendaciones,
        )
        if report is None:
            report = ServicioInforme(
                id_servicio=service.id_servicio,
                accion_realizada=accion_realizada,
                diagnostico_fisico=diagnostico_fisico,
                observaciones=encoded_notes,
            )
            db.add(report)
            db.flush()
        else:
            report.accion_realizada = accion_realizada
            report.diagnostico_fisico = diagnostico_fisico
            report.observaciones = encoded_notes

        db.execute(
            delete(ServicioRepuesto).where(ServicioRepuesto.id_servicio == service.id_servicio)
        )
        db.flush()

        for item in used_items:
            db.add(
                ServicioRepuesto(
                    id_servicio=service.id_servicio,
                    descripcion=item.descripcion,
                    cantidad=item.cantidad,
                    costo_unitario=item.costo_unitario,
                )
            )

        new_evidence_rows: list[Evidencia] = []
        for image in final_images:
            stored = storage.save_service_file(
                service_id=service.id_servicio,
                folder="cierre",
                upload=image,
            )
            stored_media.append(stored)
            evidence = Evidencia(
                tipo_evidencia="IMAGEN",
                categoria="CIERRE",
                url_archivo=stored.locator,
                mime_type=stored.mime_type,
                tamano_bytes=stored.size_bytes,
                id_servicio=service.id_servicio,
                id_incidente=incident.id_incidente,
            )
            db.add(evidence)
            new_evidence_rows.append(evidence)

        if new_evidence_rows:
            db.flush()

        all_final_evidences = _get_final_service_evidences(service) + new_evidence_rows
        if all_final_evidences:
            all_final_evidences = sorted(
                {item.id_evidencia: item for item in all_final_evidences if item.id_evidencia is not None}.values(),
                key=lambda item: item.id_evidencia,
            )
            report.foto_cierre_url = all_final_evidences[0].url_archivo
        elif report.foto_cierre_url is None and service.evidencias:
            existing = _get_final_service_evidences(service)
            if existing:
                report.foto_cierre_url = existing[0].url_archivo

        service.costo_repuestos = total_additional_cost
        base_mano_obra = Decimal(service.costo_mano_obra or 0)
        service.costo_total = (base_mano_obra + total_additional_cost).quantize(Decimal("0.01"))
        service.estado = REPAIR_REPORT_NEXT_STATE
        service.confirmacion_cliente = None
        service.fecha_confirmacion_cliente = None
        service.observaciones_cierre = None

        db.add(
            _create_bitacora_event(
                admin_user=current_user,
                incident=incident,
                request_row=service.solicitud,
                accion="INFORME_REPARACION_GUARDADO",
                descripcion="El operario registro o actualizo el informe tecnico de reparacion.",
                datos_nuevos={
                    "previous_state": previous_state,
                    "new_state": service.estado,
                    "total_spare_parts_cost": str(total_additional_cost),
                    "used_item_count": len(used_items),
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
                id_servicio=service.id_servicio,
            )
        )
        db.add(
            _create_bitacora_event(
                admin_user=current_user,
                incident=incident,
                request_row=service.solicitud,
                accion="REPUESTOS_SERVICIO_REGISTRADOS",
                descripcion="Se registraron repuestos o materiales utilizados en el servicio.",
                datos_nuevos={
                    "used_item_count": len(used_items),
                    "total_spare_parts_cost": str(total_additional_cost),
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
                id_servicio=service.id_servicio,
            )
        )
        if new_evidence_rows:
            db.add(
                _create_bitacora_event(
                    admin_user=current_user,
                    incident=incident,
                    request_row=service.solicitud,
                    accion="EVIDENCIA_CIERRE_REGISTRADA",
                    descripcion="Se registraron evidencias finales del servicio.",
                    datos_nuevos={"final_evidence_count": len(new_evidence_rows)},
                    ip_origen=ip_origen,
                    user_agent=user_agent,
                    id_servicio=service.id_servicio,
                )
            )
        if previous_state != service.estado:
            db.add(
                _create_bitacora_event(
                    admin_user=current_user,
                    incident=incident,
                    request_row=service.solicitud,
                    accion="SERVICIO_LISTO_PARA_VALIDACION",
                    descripcion="El servicio quedo listo para validacion y cierre del cliente.",
                    datos_nuevos={
                        "previous_state": previous_state,
                        "new_state": service.estado,
                    },
                    ip_origen=ip_origen,
                    user_agent=user_agent,
                    id_servicio=service.id_servicio,
                )
            )

        client_user = _get_client_user(db, cliente_id=incident.id_cliente)
        _create_service_notification(
            db=db,
            user=client_user,
            service=service,
            title="Informe tecnico completado",
            message="El operario completo el informe tecnico y el servicio esta listo para validacion.",
            payload={
                "service_id": service.id_servicio,
                "incident_id": incident.id_incidente,
                "service_state": service.estado,
                "total_additional_cost": str(total_additional_cost),
            },
        )
        for admin_user in _get_workshop_admin_users(
            db,
            workshop_id=service.solicitud.id_taller,
        ):
            _create_service_notification(
                db=db,
                user=admin_user,
                service=service,
                title="Informe de reparacion disponible",
                message=(
                    f"El operario completo el informe del servicio {service.id_servicio}."
                ),
                payload={
                    "service_id": service.id_servicio,
                    "incident_id": incident.id_incidente,
                    "service_state": service.estado,
                },
            )

        db.commit()
    except HTTPException:
        db.rollback()
        storage.delete_many(stored_media)
        raise
    except StorageError as exc:
        db.rollback()
        storage.delete_many(stored_media)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Final evidence images could not be stored.",
        ) from exc
    except (IntegrityError, SQLAlchemyError) as exc:
        db.rollback()
        storage.delete_many(stored_media)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repair report could not be persisted.",
        ) from exc

    db.expire_all()
    refreshed_service = _get_assigned_operario_service(
        db=db,
        service_id=service.id_servicio,
        operario_id=current_user.id_persona,
    )
    snapshot = _build_repair_snapshot(refreshed_service)
    return RepairReportSaveResponse(
        service_id=refreshed_service.id_servicio,
        service_state=refreshed_service.estado,
        incident_id=incident.id_incidente,
        report_id=snapshot.report_id if snapshot.report_id is not None else 0,
        accion_realizada=snapshot.accion_realizada or accion_realizada,
        diagnostico_fisico=snapshot.diagnostico_fisico,
        observaciones=snapshot.observaciones,
        recomendaciones=snapshot.recomendaciones,
        total_additional_cost=snapshot.total_additional_cost,
        used_items=snapshot.used_items,
        final_evidences=snapshot.final_evidences,
        saved_at=snapshot.saved_at or utc_now(),
        message="Repair report saved successfully.",
    )


def _build_accept_response(
    *,
    request_row: SolicitudServicio,
    service: Servicio,
    prequotation_payload: dict[str, Any] | None,
    message: str,
) -> WorkshopRequestDecisionResponse:
    return WorkshopRequestDecisionResponse(
        request_id=request_row.id_solicitud,
        request_status=request_row.estado,
        incident_id=request_row.id_incidente,
        incident_new_state=request_row.incidente.estado,
        workshop=_build_workshop_summary(request_row),
        service_id=service.id_servicio,
        service_state=service.estado,
        prequotation_code=service.codigo_precotizacion,
        prequotation_min=service.monto_precotizado_min,
        prequotation_max=service.monto_precotizado_max,
        prequotation_currency=(
            PREQUOTATION_CURRENCY if service.codigo_precotizacion is not None else None
        ),
        catalog_service_name=(
            str(prequotation_payload.get("catalog_service_name"))
            if prequotation_payload is not None
            and prequotation_payload.get("catalog_service_name") is not None
            else None
        ),
        message=message,
    )


def assign_operario_to_service(
    *,
    service_id: int,
    payload: AssignOperarioRequest,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> AssignOperarioResponse:
    service = _get_workshop_service(
        db=db,
        service_id=service_id,
        workshop_id=admin_context.workshop_id,
    )
    incident = _validate_service_assignment_eligible(service)

    operario = (
        db.execute(
            _build_operario_query().where(
                Operario.id_persona == payload.id_persona_operario,
                Operario.id_taller == admin_context.workshop_id,
            )
        )
        .unique()
        .scalars()
        .one_or_none()
    )
    if operario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operario candidate not found for this workshop.",
        )
    if not operario.activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operario is inactive and cannot be assigned.",
        )
    if operario.estado_disponibilidad not in AVAILABLE_OPERARIO_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operario is not currently available for assignment.",
        )

    matched_specialty = _get_matching_specialty_association(
        operario,
        specialty_id=incident.id_especialidad_detectada,
    )
    if matched_specialty is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operario does not match the detected specialty of the incident.",
        )

    now = utc_now()
    service.id_persona_operario = operario.id_persona
    service.fecha_asignacion_operario = now
    service.estado = ASSIGNED_SERVICE_STATE
    operario.estado_disponibilidad = "EN_SERVICIO"

    client_user = _get_client_user(db, cliente_id=incident.id_cliente)
    operario_user = _get_operario_user(db, operario_id=operario.id_persona)

    db.add(
        _create_bitacora_event(
            admin_user=admin_context.user,
            incident=incident,
            request_row=service.solicitud,
            accion="OPERARIO_ASIGNADO_SERVICIO",
            descripcion="Se asigno un operario especifico al servicio aceptado.",
            datos_nuevos={
                "id_servicio": service.id_servicio,
                "id_persona_operario": operario.id_persona,
                "estado_servicio": service.estado,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
            id_servicio=service.id_servicio,
        )
    )
    db.add(
        _create_bitacora_event(
            admin_user=admin_context.user,
            incident=incident,
            request_row=service.solicitud,
            accion="SERVICIO_ASIGNADO",
            descripcion="El servicio quedo listo para la etapa operativa del operario asignado.",
            datos_nuevos={
                "id_servicio": service.id_servicio,
                "estado_servicio": service.estado,
                "fecha_asignacion_operario": now.isoformat(),
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
            id_servicio=service.id_servicio,
        )
    )

    _create_operario_notification(
        db=db,
        operario_user=operario_user,
        service=service,
        title="Nuevo servicio asignado",
        message=(
            f"Se te asigno el servicio {service.id_servicio} para el incidente "
            f"{incident.id_incidente}."
        ),
        payload={
            "service_id": service.id_servicio,
            "incident_id": incident.id_incidente,
            "detected_specialty": incident.especialidad_detectada.nombre,
            "ai_summary": incident.diagnostico_ia_resumen,
        },
    )
    _create_client_notification(
        db=db,
        client_user=client_user,
        request_row=service.solicitud,
        title="Operario asignado",
        message="Un operario fue asignado a tu caso y el servicio sigue avanzando.",
        payload={
            "service_id": service.id_servicio,
            "incident_id": incident.id_incidente,
            "operario_id": operario.id_persona,
            "service_state": service.estado,
        },
        service_id=service.id_servicio,
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operario assignment conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Operario could not be assigned to the service.",
        ) from exc

    refreshed_service = _get_workshop_service(
        db=db,
        service_id=service.id_servicio,
        workshop_id=admin_context.workshop_id,
    )
    refreshed_operario = refreshed_service.operario
    if refreshed_operario is None:
        refreshed_operario = (
            db.execute(
                _build_operario_query().where(
                    Operario.id_persona == refreshed_service.id_persona_operario,
                    Operario.id_taller == admin_context.workshop_id,
                )
            )
            .unique()
            .scalars()
            .one_or_none()
        )
    if refreshed_operario is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assigned operario could not be loaded.",
        )
    refreshed_match = _get_matching_specialty_association(
        refreshed_operario,
        specialty_id=incident.id_especialidad_detectada,
    )
    if refreshed_match is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assigned operario specialty context could not be loaded.",
        )

    return AssignOperarioResponse(
        service_id=refreshed_service.id_servicio,
        service_state=refreshed_service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        request_id=refreshed_service.id_solicitud,
        assignment_timestamp=refreshed_service.fecha_asignacion_operario,
        assigned_operario=_build_assigned_operario_summary(
            refreshed_operario,
            matched_specialty=refreshed_match,
        ),
        message="Operario assigned successfully.",
    )


def _accept_workshop_request(
    *,
    request_row: SolicitudServicio,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopRequestDecisionResponse:
    if request_row.estado == "ACEPTADA":
        service = request_row.servicio
        if service is None:
            service = db.scalar(
                select(Servicio).where(Servicio.id_solicitud == request_row.id_solicitud)
            )
        if service is not None:
            prequotation_payload = _get_latest_prequotation_payload(
                db=db,
                service_id=service.id_servicio,
            )
            return _build_accept_response(
                request_row=request_row,
                service=service,
                prequotation_payload=prequotation_payload,
                message="Workshop request was already accepted.",
            )
    elif request_row.estado != "PENDIENTE" or not request_row.es_actual:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workshop request is not in a decidable state.",
        )

    _validate_prequotation_prerequisites(request_row.incidente)
    selected_catalog = _select_catalog_service_for_prequotation(
        db=db,
        incident=request_row.incidente,
        workshop_id=request_row.id_taller,
    )

    client_user = _get_client_user(db, cliente_id=request_row.incidente.id_cliente)
    now = utc_now()
    request_row.estado = "ACEPTADA"
    request_row.fecha_respuesta = now
    request_row.motivo_cierre = None
    request_row.incidente.estado = "EN_PROCESO"

    service = request_row.servicio
    created_service = False
    if service is None:
        service = db.scalar(
            select(Servicio).where(Servicio.id_solicitud == request_row.id_solicitud)
        )
    if service is None:
        service = Servicio(
            id_solicitud=request_row.id_solicitud,
            estado="EN_ESPERA_ASIGNACION",
        )
        db.add(service)
        db.flush()
        created_service = True

    _, prequotation_payload = _apply_service_prequotation(
        db=db,
        incident=request_row.incidente,
        request_row=request_row,
        service=service,
        catalog_row=selected_catalog,
    )

    db.add(
        _create_bitacora_event(
            admin_user=admin_context.user,
            incident=request_row.incidente,
            request_row=request_row,
            accion="SOLICITUD_ACEPTADA",
            descripcion="El taller acepto la solicitud de servicio.",
            datos_nuevos={
                "estado_solicitud": "ACEPTADA",
                "estado_incidente": request_row.incidente.estado,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
            id_servicio=service.id_servicio,
        )
    )
    db.add(
        _create_prequotation_bitacora_event(
            admin_context=admin_context,
            incident=request_row.incidente,
            request_row=request_row,
            service=service,
            payload=prequotation_payload,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    if created_service:
        db.add(
            _create_bitacora_event(
                admin_user=admin_context.user,
                incident=request_row.incidente,
                request_row=request_row,
                accion="SERVICIO_CREADO_DESDE_SOLICITUD",
                descripcion="Se creo el servicio a la espera de asignacion de operario.",
                datos_nuevos={
                    "id_servicio": service.id_servicio,
                    "estado_servicio": service.estado,
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
                id_servicio=service.id_servicio,
            )
        )

    _create_client_notification(
        db=db,
        client_user=client_user,
        request_row=request_row,
        title="Solicitud aceptada",
        message=(
            f"El taller {request_row.taller.nombre_comercial} acepto tu solicitud. "
            "El servicio quedo en espera de asignacion de operario. "
            "La precotizacion es referencial antes del diagnostico fisico."
        ),
        payload={
            "incident_id": request_row.id_incidente,
            "request_id": request_row.id_solicitud,
            "service_id": service.id_servicio,
            "service_state": service.estado,
            "codigo_precotizacion": service.codigo_precotizacion,
            "monto_precotizado_min": str(service.monto_precotizado_min),
            "monto_precotizado_max": str(service.monto_precotizado_max),
            "currency": PREQUOTATION_CURRENCY,
            "catalog_service_name": selected_catalog.nombre,
            "incluye_repuestos_basicos": selected_catalog.incluye_repuestos_basicos,
        },
        service_id=service.id_servicio,
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service acceptance conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workshop request could not be accepted.",
        ) from exc

    refreshed_request = _get_workshop_request(
        db=db,
        request_id=request_row.id_solicitud,
        workshop_id=admin_context.workshop_id,
    )
    refreshed_service = refreshed_request.servicio
    if refreshed_service is None:
        refreshed_service = db.scalar(
            select(Servicio).where(Servicio.id_solicitud == refreshed_request.id_solicitud)
        )
    if refreshed_service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Accepted service could not be loaded.",
        )
    return _build_accept_response(
        request_row=refreshed_request,
        service=refreshed_service,
        prequotation_payload=_get_latest_prequotation_payload(
            db=db,
            service_id=refreshed_service.id_servicio,
        ),
        message="Workshop request accepted and service created.",
    )


def _reject_workshop_request(
    *,
    request_row: SolicitudServicio,
    payload: WorkshopRequestDecisionRequest,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopRequestDecisionResponse:
    if request_row.estado != "PENDIENTE" or not request_row.es_actual:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workshop request is not in a decidable state.",
        )

    client_user = _get_client_user(db, cliente_id=request_row.incidente.id_cliente)
    now = utc_now()
    request_row.estado = "RECHAZADA"
    request_row.es_actual = False
    request_row.fecha_respuesta = now
    request_row.motivo_cierre = payload.motivo
    request_row.incidente.estado = "DIAGNOSTICADO"

    db.add(
        _create_bitacora_event(
            admin_user=admin_context.user,
            incident=request_row.incidente,
            request_row=request_row,
            accion="SOLICITUD_RECHAZADA",
            descripcion="El taller rechazo la solicitud de servicio.",
            datos_nuevos={
                "estado_solicitud": "RECHAZADA",
                "motivo_cierre": payload.motivo,
                "estado_incidente": "DIAGNOSTICADO",
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    db.add(
        _create_bitacora_event(
            admin_user=admin_context.user,
            incident=request_row.incidente,
            request_row=request_row,
            accion="MATCHMAKING_REINTENTO_SOLICITADO",
            descripcion="El rechazo del taller activo disparo un nuevo intento de matchmaking.",
            datos_nuevos={"id_solicitud_rechazada": request_row.id_solicitud},
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    _create_client_notification(
        db=db,
        client_user=client_user,
        request_row=request_row,
        title="Solicitud rechazada",
        message=(
            f"El taller {request_row.taller.nombre_comercial} rechazo tu solicitud. "
            "Se buscara un nuevo taller."
        ),
        payload={
            "incident_id": request_row.id_incidente,
            "request_id": request_row.id_solicitud,
            "decision": "RECHAZADA",
            "motivo": payload.motivo,
        },
    )

    try:
        rematch_response = rematch_incident_after_workshop_rejection(
            incident=request_row.incidente,
            current_user=admin_context.user,
            client_user=client_user,
            db=db,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workshop rejection could not trigger a new matchmaking attempt.",
        ) from exc

    return WorkshopRequestDecisionResponse(
        request_id=request_row.id_solicitud,
        request_status="RECHAZADA",
        incident_id=request_row.id_incidente,
        incident_new_state=rematch_response.new_state,
        workshop=_build_workshop_summary(request_row),
        next_request_id=rematch_response.request_id,
        no_candidate_after_rejection=rematch_response.no_candidate,
        next_selected_workshop=(
            WorkshopSummaryResponse(
                id_taller=rematch_response.selected_workshop.id_taller,
                nombre_comercial=rematch_response.selected_workshop.nombre_comercial,
            )
            if rematch_response.selected_workshop is not None
            else None
        ),
        message=(
            "Workshop request rejected and matchmaking re-run completed."
            if not rematch_response.no_candidate
            else "Workshop request rejected and no more candidate workshops are available."
        ),
    )


def decide_workshop_request(
    *,
    request_id: int,
    payload: WorkshopRequestDecisionRequest,
    admin_context: WorkshopAdminContext,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> WorkshopRequestDecisionResponse:
    request_row = _get_workshop_request(
        db=db,
        request_id=request_id,
        workshop_id=admin_context.workshop_id,
    )
    now = utc_now()
    was_expired = _normalize_expired_request(
        db=db,
        request_row=request_row,
        admin_context=admin_context,
        ip_origen=ip_origen,
        user_agent=user_agent,
        now=now,
    )
    if was_expired:
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workshop request expiration could not be persisted.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workshop request expired before it could be decided.",
        )

    if payload.decision == "ACEPTAR":
        return _accept_workshop_request(
            request_row=request_row,
            admin_context=admin_context,
            db=db,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    return _reject_workshop_request(
        request_row=request_row,
        payload=payload,
        admin_context=admin_context,
        db=db,
        ip_origen=ip_origen,
        user_agent=user_agent,
    )
