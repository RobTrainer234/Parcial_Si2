from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.models import (
    Administrador,
    Bitacora,
    CoberturaEspecialidad,
    Especialidad,
    Evidencia,
    Incidente,
    Notificacion,
    Seguro,
    Servicio,
    SolicitudServicio,
    Taller,
    TallerEspecialidad,
    TipoCobertura,
    Usuario,
    Vehiculo,
)
from app.packages.seguridad_usuarios.security import utc_now

from .ai_provider import (
    AIMediaInput,
    TriageProviderError,
    TriageProviderInvalidResponseError,
    TriageProviderNotConfiguredError,
    run_multimodal_triage,
)
from .audio_provider import (
    AudioProviderError,
    AudioProviderNotConfiguredError,
    AudioTranscriptionInput,
    transcribe_audio,
)
from .diagnosis_utils import (
    MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
    NO_AUDIO_ANALYSIS,
    SPEECH_TRANSCRIPTION_ANALYSIS,
    TriageDiagnosisDetails,
    build_triage_details_from_ai_result,
    build_triage_details_from_payload,
    build_triage_payload,
    normalize_catalog_name,
)
from .matchmaking import RankedWorkshopCandidate, build_ranked_candidate, candidate_sort_key
from .schemas import (
    IncidentClassificationResponse,
    IncidentDetailResponse,
    IncidentEvidenceResponse,
    IncidentEvidenceSummaryResponse,
    IncidentReportCreateData,
    IncidentReportResponse,
    MatchmakingActiveRequestResponse,
    MatchmakingSelectionResponse,
    MatchmakingStatusResponse,
    OperarioAssignedServiceSummary,
    OperarioServiceWorkshopSummary,
    OperarioStructuredProfileResponse,
    SpecialtySummaryResponse,
    StructuredProfileAcknowledgeResponse,
    WorkshopCandidateSummary,
)
from .storage import (
    AUDIO_MIME_PREFIX,
    build_public_media_url,
    IMAGE_MIME_PREFIX,
    StoredMedia,
    StorageError,
    get_triage_storage,
)


MAX_IMAGE_FILES = 5
MAX_AUDIO_FILE_BYTES = 25 * 1024 * 1024
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".webm", ".aac"}
NON_VERBAL_AUDIO_NOTE = (
    "Audio no verbal o sonido mecanico detectado. No se obtuvo transcripcion util."
)
AUDIO_TRANSCRIPTION_UNAVAILABLE_NOTE = (
    "No se pudo transcribir el audio automaticamente. Se requiere revision manual."
)
TRIAGE_ELIGIBLE_STATES = {"EN_TRIAJE", "DIAGNOSTICADO"}
MATCHMAKING_ELIGIBLE_STATES = {"EN_TRIAJE", "DIAGNOSTICADO", "EN_MATCHMAKING"}
OPERARIO_PROFILE_ALLOWED_SERVICE_STATES = {
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
OPERARIO_PROFILE_ALLOWED_INCIDENT_STATES = {"DIAGNOSTICADO", "EN_MATCHMAKING", "EN_PROCESO"}
settings = get_settings()
logger = logging.getLogger(__name__)


def _build_incident_query():
    return select(Incidente).options(
        joinedload(Incidente.especialidad_reportada_cliente),
        joinedload(Incidente.especialidad_detectada),
        selectinload(Incidente.evidencias),
        selectinload(Incidente.solicitudes).joinedload(SolicitudServicio.taller),
    )


def _build_operario_service_query():
    return select(Servicio).options(
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.taller),
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.incidente)
        .joinedload(Incidente.especialidad_reportada_cliente),
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.incidente)
        .joinedload(Incidente.especialidad_detectada),
        joinedload(Servicio.solicitud)
        .joinedload(SolicitudServicio.incidente)
        .selectinload(Incidente.evidencias),
    )


def _validate_files(
    *,
    audio_file: UploadFile | None,
    image_files: Sequence[UploadFile],
) -> None:
    if len(image_files) > MAX_IMAGE_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A maximum of {MAX_IMAGE_FILES} images is allowed.",
        )

    if audio_file is not None:
        content_type = audio_file.content_type or ""
        extension = Path(audio_file.filename or "").suffix.lower()
        if not content_type.startswith(AUDIO_MIME_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid audio file type.",
            )
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid audio file extension.",
            )
        if _get_upload_size_bytes(audio_file) > MAX_AUDIO_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file is too large.",
            )

    for image in image_files:
        content_type = image.content_type or ""
        if not content_type.startswith(IMAGE_MIME_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file type.",
            )


def _get_upload_size_bytes(upload: UploadFile) -> int:
    try:
        current_position = upload.file.tell()
        upload.file.seek(0, 2)
        size = upload.file.tell()
        upload.file.seek(current_position)
        return max(size, 0)
    except (AttributeError, OSError, ValueError):
        return 0


def _normalize_multiline_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _is_meaningful_audio_transcript(value: str | None) -> bool:
    normalized = _normalize_multiline_text(value)
    if normalized is None:
        return False
    lowered = normalized.lower()
    if lowered in {
        NON_VERBAL_AUDIO_NOTE.lower(),
        AUDIO_TRANSCRIPTION_UNAVAILABLE_NOTE.lower(),
        "[music]",
        "[silence]",
        "(silence)",
        "...",
    }:
        return False
    letters = sum(1 for char in normalized if char.isalpha())
    return letters >= 6 and len(normalized) >= 8


def _build_audio_summary(
    *,
    audio_analysis_type: str,
    transcript_text: str | None,
) -> str | None:
    if audio_analysis_type == NO_AUDIO_ANALYSIS:
        return None
    if audio_analysis_type == SPEECH_TRANSCRIPTION_ANALYSIS and transcript_text:
        return (
            "Audio con explicacion verbal del cliente. "
            f"Transcripcion relevante: {transcript_text[:280]}"
        )
    return (
        "Audio sin voz clara o con sonido mecanico. "
        "El analisis acustico se trata como evidencia experimental y requiere validacion manual."
    )


def _transcribe_audio_media(
    audio_input: AIMediaInput,
) -> tuple[str | None, str, str | None, str | None]:
    try:
        result = transcribe_audio(
            audio_input=AudioTranscriptionInput(
                content_bytes=audio_input.content_bytes,
                filename=Path(audio_input.locator).name or "incident-audio.webm",
                mime_type=audio_input.mime_type,
            ),
            prompt=(
                "Transcribe fielmente la voz del cliente en espanol si existe. "
                "Si el audio solo contiene ruido, motor o sonidos mecanicos, devuelve el mejor resultado posible."
            ),
        )
    except (AudioProviderError, AudioProviderNotConfiguredError) as exc:
        logger.warning("Audio transcription failed: %s", exc)
        return (
            AUDIO_TRANSCRIPTION_UNAVAILABLE_NOTE,
            MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
            _build_audio_summary(
                audio_analysis_type=MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
                transcript_text=None,
            ),
            "audio_transcription_failed",
        )

    if _is_meaningful_audio_transcript(result.transcript_text):
        transcript_text = _normalize_multiline_text(result.transcript_text)
        return (
            transcript_text,
            SPEECH_TRANSCRIPTION_ANALYSIS,
            _build_audio_summary(
                audio_analysis_type=SPEECH_TRANSCRIPTION_ANALYSIS,
                transcript_text=transcript_text,
            ),
            result.warning,
        )

    return (
        NON_VERBAL_AUDIO_NOTE,
        MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
        _build_audio_summary(
            audio_analysis_type=MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
            transcript_text=None,
        ),
        result.warning or "non_verbal_or_mechanical_sound_detected",
    )


def _get_owned_vehicle(db: Session, *, vehicle_id: int, cliente_id: int) -> Vehiculo:
    vehicle = db.scalar(
        select(Vehiculo).where(
            Vehiculo.id_vehiculo == vehicle_id,
            Vehiculo.id_persona == cliente_id,
        )
    )
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )
    return vehicle


def _get_specialty(db: Session, specialty_id: int) -> Especialidad:
    specialty = db.get(Especialidad, specialty_id)
    if specialty is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reported specialty does not exist.",
        )
    return specialty


def _create_bitacora_event(
    *,
    user: Usuario,
    incident: Incidente,
    accion: str,
    tipo_evento: str,
    descripcion: str,
    datos_nuevos: dict[str, Any] | None,
    ip_origen: str | None,
    user_agent: str | None,
    id_solicitud: int | None = None,
) -> Bitacora:
    return Bitacora(
        accion=accion,
        tipo_evento=tipo_evento,
        descripcion=descripcion,
        entidad_principal="INCIDENTE",
        id_entidad_principal=incident.id_incidente,
        datos_nuevos=datos_nuevos,
        ip_origen=ip_origen,
        user_agent=user_agent,
        hash_evento="",
        id_usuario=user.id_usuario,
        id_incidente=incident.id_incidente,
        id_solicitud=id_solicitud,
    )


def _serialize_evidence(evidence: Evidencia) -> IncidentEvidenceResponse:
    return IncidentEvidenceResponse(
        id_evidencia=evidence.id_evidencia,
        tipo_evidencia=evidence.tipo_evidencia,
        categoria=evidence.categoria,
        url_archivo=build_public_media_url(evidence.url_archivo),
        mime_type=evidence.mime_type,
        tamano_bytes=evidence.tamano_bytes,
        fecha_registro=evidence.fecha_registro,
    )


def _build_evidence_summary(evidences: list[Evidencia]) -> IncidentEvidenceSummaryResponse:
    imagenes = sum(1 for item in evidences if item.tipo_evidencia == "IMAGEN")
    audio = sum(1 for item in evidences if item.tipo_evidencia == "AUDIO")
    return IncidentEvidenceSummaryResponse(
        total=len(evidences),
        imagenes=imagenes,
        audio=audio,
    )


def _build_specialty_summary(specialty: Especialidad | None) -> SpecialtySummaryResponse | None:
    if specialty is None:
        return None
    return SpecialtySummaryResponse(
        id_especialidad=specialty.id_especialidad,
        nombre=specialty.nombre,
    )


def _normalize_catalog_name(value: str | None) -> str | None:
    return normalize_catalog_name(value)


def _build_triage_details(incident: Incidente) -> TriageDiagnosisDetails:
    detected_specialty_name = (
        incident.especialidad_detectada.nombre
        if incident.especialidad_detectada is not None
        else None
    )
    return build_triage_details_from_payload(
        payload=incident.diagnostico_ia_json,
        detected_specialty_name=detected_specialty_name,
        summary=incident.diagnostico_ia_resumen,
        severity=incident.severidad,
        confidence=incident.confianza_ia,
        requires_manual_review=incident.requiere_revision_manual,
    )


def _resolve_audio_response_fields(
    incident: Incidente,
    triage_details: TriageDiagnosisDetails,
) -> tuple[str | None, str]:
    if triage_details.audio_analysis_type != NO_AUDIO_ANALYSIS:
        return triage_details.audio_summary, triage_details.audio_analysis_type
    if _is_meaningful_audio_transcript(incident.transcripcion_audio):
        return (
            _build_audio_summary(
                audio_analysis_type=SPEECH_TRANSCRIPTION_ANALYSIS,
                transcript_text=incident.transcripcion_audio,
            ),
            SPEECH_TRANSCRIPTION_ANALYSIS,
        )
    if incident.transcripcion_audio in {
        NON_VERBAL_AUDIO_NOTE,
        AUDIO_TRANSCRIPTION_UNAVAILABLE_NOTE,
    }:
        return (
            _build_audio_summary(
                audio_analysis_type=MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
                transcript_text=None,
            ),
            MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
        )
    return None, NO_AUDIO_ANALYSIS


def _build_incident_detail_response(incident: Incidente) -> IncidentDetailResponse:
    ordered_evidences = sorted(incident.evidencias, key=lambda item: item.id_evidencia)
    triage_details = _build_triage_details(incident)
    audio_summary, audio_analysis_type = _resolve_audio_response_fields(
        incident,
        triage_details,
    )
    return IncidentDetailResponse(
        incident_id=incident.id_incidente,
        status=incident.estado,
        fecha_hora=incident.fecha_hora,
        latitud=incident.latitud,
        longitud=incident.longitud,
        descripcion_cliente=incident.descripcion_cliente,
        id_vehiculo=incident.id_vehiculo,
        especialidad_reportada=_build_specialty_summary(incident.especialidad_reportada_cliente),
        especialidad_detectada=_build_specialty_summary(incident.especialidad_detectada),
        severity=triage_details.severity,
        diagnostico_ia_resumen=incident.diagnostico_ia_resumen,
        summary=triage_details.summary,
        specific_diagnosis=triage_details.specific_diagnosis,
        suggested_service=triage_details.suggested_service,
        customer_recommendation=triage_details.customer_recommendation,
        operator_notes=triage_details.operator_notes,
        visual_evidence_tags=triage_details.visual_evidence_tags,
        audio_summary=audio_summary,
        audio_analysis_type=audio_analysis_type,
        diagnostico_ia_json=incident.diagnostico_ia_json,
        confianza_ia=incident.confianza_ia,
        transcripcion_audio=incident.transcripcion_audio,
        etiquetas_imagen=incident.etiquetas_imagen,
        fecha_triaje=incident.fecha_triaje,
        requiere_revision_manual=incident.requiere_revision_manual,
        evidences=[_serialize_evidence(item) for item in ordered_evidences],
        evidence_summary=_build_evidence_summary(ordered_evidences),
    )


def _build_incident_report_response(
    incident: Incidente,
    *,
    message: str,
) -> IncidentReportResponse:
    ordered_evidences = sorted(incident.evidencias, key=lambda item: item.id_evidencia)
    return IncidentReportResponse(
        incident_id=incident.id_incidente,
        status=incident.estado,
        message=message,
        id_vehiculo=incident.id_vehiculo,
        latitud=incident.latitud,
        longitud=incident.longitud,
        descripcion_cliente=incident.descripcion_cliente,
        especialidad_reportada=_build_specialty_summary(incident.especialidad_reportada_cliente),
        evidence_summary=_build_evidence_summary(ordered_evidences),
        evidences=[_serialize_evidence(item) for item in ordered_evidences],
        fecha_hora=incident.fecha_hora,
    )


def _extract_profile_list(value: Any) -> list[str] | None:
    if isinstance(value, list):
        extracted = [str(item).strip() for item in value if str(item).strip()]
        return extracted or None
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else None
    return None


def _extract_profile_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _extract_profile_str(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _get_assigned_service(
    db: Session,
    *,
    service_id: int,
    operario_id: int,
) -> Servicio:
    service = db.scalar(
        _build_operario_service_query().where(
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


def _validate_structured_profile_ready(service: Servicio) -> Incidente:
    incident = service.solicitud.incidente
    if service.estado not in OPERARIO_PROFILE_ALLOWED_SERVICE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not in a valid state for the structured profile.",
        )
    if incident.estado not in OPERARIO_PROFILE_ALLOWED_INCIDENT_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident is not in a compatible state for the structured profile.",
        )
    if (
        incident.fecha_triaje is None
        or incident.id_especialidad_detectada is None
        or incident.severidad is None
        or (incident.diagnostico_ia_resumen is None and incident.diagnostico_ia_json is None)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI triage result is not ready for this service.",
        )
    return incident


def _build_operario_assigned_service_summary(service: Servicio) -> OperarioAssignedServiceSummary:
    incident = service.solicitud.incidente
    return OperarioAssignedServiceSummary(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        detected_specialty=_build_specialty_summary(incident.especialidad_detectada),
        severity=incident.severidad,
        ai_summary=incident.diagnostico_ia_resumen,
        prequotation_code=service.codigo_precotizacion,
        prequotation_min=service.monto_precotizado_min,
        prequotation_max=service.monto_precotizado_max,
        prequotation_currency="BOB" if service.codigo_precotizacion is not None else None,
    )


def _build_operario_structured_profile_response(
    service: Servicio,
) -> OperarioStructuredProfileResponse:
    incident = service.solicitud.incidente
    ordered_evidences = sorted(incident.evidencias, key=lambda item: item.id_evidencia)
    diagnostico = incident.diagnostico_ia_json or {}
    triage_details = _build_triage_details(incident)
    audio_summary, audio_analysis_type = _resolve_audio_response_fields(
        incident,
        triage_details,
    )
    return OperarioStructuredProfileResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        latitud=incident.latitud,
        longitud=incident.longitud,
        workshop=OperarioServiceWorkshopSummary(
            id_taller=service.solicitud.taller.id_taller,
            nombre_comercial=service.solicitud.taller.nombre_comercial,
        ),
        client_reported_specialty=_build_specialty_summary(
            incident.especialidad_reportada_cliente
        ),
        detected_specialty=_build_specialty_summary(incident.especialidad_detectada),
        severity=incident.severidad,
        confidence=incident.confianza_ia,
        ai_summary=incident.diagnostico_ia_resumen,
        summary=triage_details.summary,
        specific_diagnosis=triage_details.specific_diagnosis,
        suggested_service=triage_details.suggested_service,
        customer_recommendation=triage_details.customer_recommendation,
        operator_notes=triage_details.operator_notes,
        visual_evidence_tags=triage_details.visual_evidence_tags,
        audio_summary=audio_summary,
        audio_analysis_type=audio_analysis_type,
        transcripcion_audio=incident.transcripcion_audio,
        etiquetas_imagen=incident.etiquetas_imagen,
        herramientas_sugeridas=_extract_profile_list(
            diagnostico.get("suggested_tools") or diagnostico.get("herramientas_sugeridas")
        ),
        requiere_grua=_extract_profile_bool(
            diagnostico.get("requires_tow") or diagnostico.get("requiere_grua")
        ),
        observaciones=_extract_profile_str(
            diagnostico.get("observations") or diagnostico.get("observaciones")
        ),
        prequotation_code=service.codigo_precotizacion,
        prequotation_min=service.monto_precotizado_min,
        prequotation_max=service.monto_precotizado_max,
        prequotation_currency="BOB" if service.codigo_precotizacion is not None else None,
        requiere_revision_manual=incident.requiere_revision_manual,
        diagnostico_ia_json=incident.diagnostico_ia_json,
        evidence_summary=_build_evidence_summary(ordered_evidences),
        evidences=[_serialize_evidence(item) for item in ordered_evidences],
    )


def _build_incident_classification_response(
    *,
    incident: Incidente,
    previous_state: str,
) -> IncidentClassificationResponse:
    triage_details = _build_triage_details(incident)
    return IncidentClassificationResponse(
        incident_id=incident.id_incidente,
        previous_state=previous_state,
        new_state=incident.estado,
        reported_specialty=_build_specialty_summary(incident.especialidad_reportada_cliente),
        detected_specialty=_build_specialty_summary(incident.especialidad_detectada),
        severity=incident.severidad,
        confidence=incident.confianza_ia,
        requires_manual_review=incident.requiere_revision_manual,
        summary=triage_details.summary,
        specific_diagnosis=triage_details.specific_diagnosis,
        suggested_service=triage_details.suggested_service,
        customer_recommendation=triage_details.customer_recommendation,
        operator_notes=triage_details.operator_notes,
        visual_evidence_tags=triage_details.visual_evidence_tags,
        audio_summary=triage_details.audio_summary,
        audio_analysis_type=triage_details.audio_analysis_type,
    )


def _build_workshop_candidate_summary(candidate: RankedWorkshopCandidate) -> WorkshopCandidateSummary:
    return WorkshopCandidateSummary(
        id_taller=candidate.taller.id_taller,
        nombre_comercial=candidate.taller.nombre_comercial,
        reputacion_prom=candidate.taller.reputacion_prom,
        radio_accion_km=candidate.taller.radio_accion_km,
        distance_km=candidate.distance_km,
    )


def _build_matchmaking_active_request_response(
    request_row: SolicitudServicio,
    *,
    incident: Incidente,
    is_expired: bool,
) -> MatchmakingActiveRequestResponse:
    candidate = build_ranked_candidate(
        incident_lat=incident.latitud,
        incident_lon=incident.longitud,
        taller=request_row.taller,
        used_insurance_priority=request_row.prioridad_seguro,
    )
    return MatchmakingActiveRequestResponse(
        request_id=request_row.id_solicitud,
        request_status=request_row.estado,
        attempt_number=request_row.intento_numero,
        expires_at=request_row.fecha_expiracion,
        used_insurance_priority=request_row.prioridad_seguro,
        score_proximidad=(
            request_row.score_proximidad
            if request_row.score_proximidad is not None
            else candidate.score_proximidad
        ),
        score_reputacion=(
            request_row.score_reputacion
            if request_row.score_reputacion is not None
            else candidate.score_reputacion
        ),
        score_total=(
            request_row.score_total
            if request_row.score_total is not None
            else candidate.score_total
        ),
        selected_workshop=_build_workshop_candidate_summary(candidate),
        is_expired=is_expired,
    )


def _build_matchmaking_selection_response(
    *,
    incident: Incidente,
    previous_state: str,
    candidate: RankedWorkshopCandidate | None,
    request_row: SolicitudServicio | None,
    message: str,
    no_candidate: bool,
) -> MatchmakingSelectionResponse:
    return MatchmakingSelectionResponse(
        incident_id=incident.id_incidente,
        previous_state=previous_state,
        new_state=incident.estado,
        detected_specialty=_build_specialty_summary(incident.especialidad_detectada),
        severity=incident.severidad,
        selected_workshop=_build_workshop_candidate_summary(candidate) if candidate else None,
        used_insurance_priority=(candidate.used_insurance_priority if candidate else None),
        request_id=request_row.id_solicitud if request_row else None,
        request_status=request_row.estado if request_row else None,
        expires_at=request_row.fecha_expiracion if request_row else None,
        score_proximidad=(candidate.score_proximidad if candidate else None),
        score_reputacion=(candidate.score_reputacion if candidate else None),
        score_total=(candidate.score_total if candidate else None),
        distance_km=(candidate.distance_km if candidate else None),
        attempt_number=request_row.intento_numero if request_row else None,
        no_candidate=no_candidate,
        message=message,
    )


def _get_owned_incident(db: Session, *, incident_id: int, cliente_id: int) -> Incidente:
    incident = db.scalar(
        _build_incident_query().where(
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


def _get_owned_incident_by_local_uuid(
    db: Session,
    *,
    cliente_id: int,
    local_uuid: str,
) -> Incidente | None:
    return db.scalar(
        _build_incident_query().where(
            Incidente.id_cliente == cliente_id,
            Incidente.local_uuid == local_uuid,
        )
    )


def _has_offline_sync_event(db: Session, *, incident_id: int) -> bool:
    return (
        db.scalar(
            select(Bitacora.id_bitacora).where(
                Bitacora.id_incidente == incident_id,
                Bitacora.accion == "INCIDENTE_OFFLINE_SINCRONIZADO",
            )
        )
        is not None
    )


def _ensure_offline_sync_event(
    *,
    db: Session,
    current_user: Usuario,
    incident: Incidente,
    offline_sync: bool,
    ip_origen: str | None,
    user_agent: str | None,
) -> bool:
    if not offline_sync or not incident.local_uuid:
        return False
    if _has_offline_sync_event(db, incident_id=incident.id_incidente):
        return False
    db.add(
        _create_bitacora_event(
            user=current_user,
            incident=incident,
            accion="INCIDENTE_OFFLINE_SINCRONIZADO",
            tipo_evento="SINCRONIZACION",
            descripcion="Se sincronizo un incidente reportado sin conexion.",
            datos_nuevos={
                "local_uuid": incident.local_uuid,
                "estado": incident.estado,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    return True


def _get_active_matchmaking_request(
    db: Session,
    *,
    incident_id: int,
) -> SolicitudServicio | None:
    return db.scalar(
        select(SolicitudServicio)
        .options(joinedload(SolicitudServicio.taller))
        .where(
            SolicitudServicio.id_incidente == incident_id,
            SolicitudServicio.es_actual.is_(True),
            SolicitudServicio.estado.in_(("PENDIENTE", "ACEPTADA")),
        )
        .order_by(SolicitudServicio.id_solicitud.desc())
    )


def _is_request_expired(request_row: SolicitudServicio, *, now) -> bool:
    return request_row.estado == "PENDIENTE" and request_row.fecha_expiracion <= now


def _validate_matchmaking_eligible(incident: Incidente) -> None:
    if incident.estado not in MATCHMAKING_ELIGIBLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident is not eligible for matchmaking.",
        )
    if incident.id_especialidad_detectada is None or incident.severidad is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident diagnosis is incomplete for matchmaking.",
        )


def _get_attempted_workshop_ids(db: Session, *, incident_id: int) -> set[int]:
    return set(
        db.scalars(
            select(SolicitudServicio.id_taller).where(
                SolicitudServicio.id_incidente == incident_id
            )
        )
    )


def _expire_pending_request(
    *,
    db: Session,
    request_row: SolicitudServicio,
    incident: Incidente,
    current_user: Usuario,
    ip_origen: str | None,
    user_agent: str | None,
) -> None:
    request_row.estado = "EXPIRADA"
    request_row.es_actual = False
    request_row.fecha_respuesta = utc_now()
    request_row.motivo_cierre = "Tiempo de respuesta agotado."
    incident.estado = "DIAGNOSTICADO"
    db.add(
        _create_bitacora_event(
            user=current_user,
            incident=incident,
            accion="SOLICITUD_EXPIRADA",
            tipo_evento="MATCHMAKING",
            descripcion="La solicitud activa expiro antes de una nueva ejecucion de matchmaking.",
            datos_nuevos={
                "id_solicitud": request_row.id_solicitud,
                "id_taller": request_row.id_taller,
                "estado": "EXPIRADA",
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
            id_solicitud=request_row.id_solicitud,
        )
    )


def _get_insured_priority_workshop_ids(
    db: Session,
    *,
    cliente_id: int,
    detected_specialty_id: int,
    eligible_workshop_ids: set[int],
    now,
) -> set[int]:
    if not eligible_workshop_ids:
        return set()

    insurances = list(
        db.scalars(
            select(Seguro)
            .options(
                joinedload(Seguro.cobertura).selectinload(TipoCobertura.especialidades)
            )
            .where(
                Seguro.id_cliente == cliente_id,
                Seguro.activo.is_(True),
                Seguro.id_taller.in_(eligible_workshop_ids),
                Seguro.fecha_inicio <= now,
                or_(Seguro.fecha_fin.is_(None), Seguro.fecha_fin >= now),
            )
        )
    )

    prioritized_ids: set[int] = set()
    for insurance in insurances:
        covered_specialty_ids = {
            coverage.id_especialidad for coverage in insurance.cobertura.especialidades
        }
        if detected_specialty_id in covered_specialty_ids:
            prioritized_ids.add(insurance.id_taller)
    return prioritized_ids


def _build_ranked_candidates(
    db: Session,
    *,
    incident: Incidente,
    attempted_workshop_ids: set[int],
    now,
) -> list[RankedWorkshopCandidate]:
    workshop_query = (
        select(Taller)
        .join(TallerEspecialidad, TallerEspecialidad.id_taller == Taller.id_taller)
        .where(
            Taller.activo.is_(True),
            TallerEspecialidad.id_especialidad == incident.id_especialidad_detectada,
            TallerEspecialidad.activo.is_(True),
        )
        .order_by(Taller.id_taller)
    )
    if attempted_workshop_ids:
        workshop_query = workshop_query.where(Taller.id_taller.not_in(attempted_workshop_ids))

    workshops = list(db.scalars(workshop_query))
    filtered_by_radius: list[Taller] = []
    provisional_candidates: list[tuple[Taller, Decimal]] = []
    for workshop in workshops:
        candidate = build_ranked_candidate(
            incident_lat=incident.latitud,
            incident_lon=incident.longitud,
            taller=workshop,
            used_insurance_priority=False,
        )
        if candidate.distance_km <= Decimal(workshop.radio_accion_km):
            filtered_by_radius.append(workshop)
            provisional_candidates.append((workshop, candidate.distance_km))

    eligible_workshop_ids = {workshop.id_taller for workshop in filtered_by_radius}
    prioritized_ids = _get_insured_priority_workshop_ids(
        db,
        cliente_id=incident.id_cliente,
        detected_specialty_id=incident.id_especialidad_detectada,
        eligible_workshop_ids=eligible_workshop_ids,
        now=now,
    )

    candidates = [
        build_ranked_candidate(
            incident_lat=incident.latitud,
            incident_lon=incident.longitud,
            taller=workshop,
            used_insurance_priority=workshop.id_taller in prioritized_ids,
        )
        for workshop, _ in provisional_candidates
    ]
    return sorted(candidates, key=candidate_sort_key)


def _get_next_attempt_number(incident: Incidente) -> int:
    if not incident.solicitudes:
        return 1
    return max(solicitud.intento_numero for solicitud in incident.solicitudes) + 1


def _create_workshop_notifications(
    *,
    db: Session,
    request_row: SolicitudServicio,
    candidate: RankedWorkshopCandidate,
    incident: Incidente,
) -> None:
    admin_users = list(
        db.scalars(
            select(Usuario)
            .join(Administrador, Administrador.id_persona == Usuario.id_persona)
            .where(
                Administrador.id_taller == candidate.taller.id_taller,
                Administrador.activo.is_(True),
                Usuario.activo.is_(True),
            )
        )
    )
    for user in admin_users:
        db.add(
            Notificacion(
                id_usuario=user.id_usuario,
                id_solicitud=request_row.id_solicitud,
                canal="WEB",
                titulo="Nueva solicitud de auxilio",
                mensaje=(
                    f"El incidente {incident.id_incidente} fue asignado a su taller "
                    f"para evaluacion inicial."
                ),
                payload={
                    "incident_id": incident.id_incidente,
                    "request_id": request_row.id_solicitud,
                    "workshop_id": candidate.taller.id_taller,
                    "used_insurance_priority": candidate.used_insurance_priority,
                },
                estado="PENDIENTE",
            )
        )


def _create_no_candidate_notification(
    *,
    db: Session,
    target_user: Usuario,
    incident: Incidente,
) -> None:
    db.add(
        Notificacion(
            id_usuario=target_user.id_usuario,
            canal="WEB",
            titulo="Sin talleres disponibles",
            mensaje=(
                f"No se encontro un taller elegible para el incidente {incident.id_incidente}."
            ),
            payload={"incident_id": incident.id_incidente, "status": incident.estado},
            estado="PENDIENTE",
        )
    )


def _execute_incident_matchmaking(
    *,
    incident: Incidente,
    current_user: Usuario,
    no_candidate_notify_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> MatchmakingSelectionResponse:
    _validate_matchmaking_eligible(incident)
    db.flush()

    previous_state = incident.estado
    now = utc_now()
    active_request = _get_active_matchmaking_request(db, incident_id=incident.id_incidente)
    if active_request is not None:
        if active_request.estado == "ACEPTADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Incident already has an accepted workshop request.",
            )
        if not _is_request_expired(active_request, now=now):
            return _build_matchmaking_selection_response(
                incident=incident,
                previous_state=previous_state,
                candidate=build_ranked_candidate(
                    incident_lat=incident.latitud,
                    incident_lon=incident.longitud,
                    taller=active_request.taller,
                    used_insurance_priority=active_request.prioridad_seguro,
                ),
                request_row=active_request,
                message="An active workshop request already exists for this incident.",
                no_candidate=False,
            )
        _expire_pending_request(
            db=db,
            request_row=active_request,
            incident=incident,
            current_user=current_user,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )

    attempted_workshop_ids = _get_attempted_workshop_ids(
        db,
        incident_id=incident.id_incidente,
    )
    candidates = _build_ranked_candidates(
        db,
        incident=incident,
        attempted_workshop_ids=attempted_workshop_ids,
        now=now,
    )

    db.add(
        _create_bitacora_event(
            user=current_user,
            incident=incident,
            accion="MATCHMAKING_INICIADO",
            tipo_evento="MATCHMAKING",
            descripcion="Se inicio el proceso de matchmaking para el incidente.",
            datos_nuevos={
                "candidate_count": len(candidates),
                "detected_specialty_id": incident.id_especialidad_detectada,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )

    if not candidates:
        incident.estado = "DIAGNOSTICADO"
        _create_no_candidate_notification(
            db=db,
            target_user=no_candidate_notify_user,
            incident=incident,
        )
        db.add(
            _create_bitacora_event(
                user=current_user,
                incident=incident,
                accion="MATCHMAKING_SIN_CANDIDATOS",
                tipo_evento="MATCHMAKING",
                descripcion="No se encontraron talleres elegibles para el incidente.",
                datos_nuevos={"candidate_count": 0},
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )
        db.commit()
        db.expire_all()
        refreshed_incident = _get_owned_incident(
            db,
            incident_id=incident.id_incidente,
            cliente_id=no_candidate_notify_user.id_persona,
        )
        return _build_matchmaking_selection_response(
            incident=refreshed_incident,
            previous_state=previous_state,
            candidate=None,
            request_row=None,
            message="No candidate workshops are currently available.",
            no_candidate=True,
        )

    top_candidate = candidates[0]
    attempt_number = _get_next_attempt_number(incident)
    fecha_expiracion = now + timedelta(seconds=settings.matchmaking_request_ttl_seconds)

    request_row = SolicitudServicio(
        id_incidente=incident.id_incidente,
        id_taller=top_candidate.taller.id_taller,
        fecha_envio=now,
        fecha_expiracion=fecha_expiracion,
        estado="PENDIENTE",
        prioridad_seguro=top_candidate.used_insurance_priority,
        score_proximidad=top_candidate.score_proximidad,
        score_reputacion=top_candidate.score_reputacion,
        score_total=top_candidate.score_total,
        ranking_posicion=1,
        intento_numero=attempt_number,
        es_actual=True,
    )
    incident.estado = "EN_MATCHMAKING"
    db.add(request_row)
    db.flush()

    if top_candidate.used_insurance_priority:
        db.add(
            _create_bitacora_event(
                user=current_user,
                incident=incident,
                accion="MATCHMAKING_PRIORIDAD_SEGURO",
                tipo_evento="MATCHMAKING",
                descripcion="La prioridad de seguro fue aplicada al taller seleccionado.",
                datos_nuevos={
                    "id_taller": top_candidate.taller.id_taller,
                    "id_solicitud": request_row.id_solicitud,
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
                id_solicitud=request_row.id_solicitud,
            )
        )

    db.add(
        _create_bitacora_event(
            user=current_user,
            incident=incident,
            accion="MATCHMAKING_CANDIDATO_SELECCIONADO",
            tipo_evento="MATCHMAKING",
            descripcion="Se selecciono el mejor taller candidato para el incidente.",
            datos_nuevos={
                "id_taller": top_candidate.taller.id_taller,
                "score_total": str(top_candidate.score_total),
                "distance_km": str(top_candidate.distance_km),
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
            id_solicitud=request_row.id_solicitud,
        )
    )
    db.add(
        _create_bitacora_event(
            user=current_user,
            incident=incident,
            accion="SOLICITUD_SERVICIO_CREADA",
            tipo_evento="MATCHMAKING",
            descripcion="Se creo una solicitud de servicio para el taller top 1.",
            datos_nuevos={
                "id_solicitud": request_row.id_solicitud,
                "id_taller": top_candidate.taller.id_taller,
                "attempt_number": attempt_number,
                "used_insurance_priority": top_candidate.used_insurance_priority,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
            id_solicitud=request_row.id_solicitud,
        )
    )
    _create_workshop_notifications(
        db=db,
        request_row=request_row,
        candidate=top_candidate,
        incident=incident,
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Matchmaking request conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Matchmaking request could not be created.",
        ) from exc

    db.expire_all()
    refreshed_incident = _get_owned_incident(
        db,
        incident_id=incident.id_incidente,
        cliente_id=no_candidate_notify_user.id_persona,
    )
    refreshed_request = _get_active_matchmaking_request(db, incident_id=incident.id_incidente)
    return _build_matchmaking_selection_response(
        incident=refreshed_incident,
        previous_state=previous_state,
        candidate=top_candidate,
        request_row=refreshed_request,
        message="Top workshop candidate selected and request created.",
        no_candidate=False,
    )


def _get_specialty_catalog(db: Session) -> tuple[list[Especialidad], dict[str, Especialidad]]:
    specialties = list(db.scalars(select(Especialidad).order_by(Especialidad.nombre)))
    specialty_map = {
        _normalize_catalog_name(item.nombre): item
        for item in specialties
    }
    return specialties, specialty_map


def _load_incident_media_inputs(
    incident: Incidente,
) -> tuple[list[AIMediaInput], AIMediaInput | None]:
    storage = get_triage_storage()
    images: list[AIMediaInput] = []
    audio_input: AIMediaInput | None = None

    for evidence in sorted(incident.evidencias, key=lambda item: item.id_evidencia):
        resolved = storage.read_locator(
            locator=evidence.url_archivo,
            mime_type=evidence.mime_type,
        )
        media_input = AIMediaInput(
            content_bytes=resolved.content_bytes,
            mime_type=(resolved.mime_type or evidence.mime_type or "application/octet-stream"),
            locator=resolved.locator,
        )
        if evidence.tipo_evidencia == "IMAGEN":
            images.append(media_input)
        elif evidence.tipo_evidencia == "AUDIO" and audio_input is None:
            audio_input = media_input

    return images, audio_input


def _resolve_incident_audio_context(
    *,
    incident: Incidente,
    audio_input: AIMediaInput | None,
) -> tuple[str | None, str, str | None, str | None]:
    if audio_input is None:
        return None, NO_AUDIO_ANALYSIS, None, None

    stored_transcript = _normalize_multiline_text(incident.transcripcion_audio)
    if _is_meaningful_audio_transcript(stored_transcript):
        return (
            stored_transcript,
            SPEECH_TRANSCRIPTION_ANALYSIS,
            _build_audio_summary(
                audio_analysis_type=SPEECH_TRANSCRIPTION_ANALYSIS,
                transcript_text=stored_transcript,
            ),
            None,
        )
    if stored_transcript == NON_VERBAL_AUDIO_NOTE:
        return (
            stored_transcript,
            MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
            _build_audio_summary(
                audio_analysis_type=MECHANICAL_SOUND_EXPERIMENTAL_ANALYSIS,
                transcript_text=None,
            ),
            "non_verbal_or_mechanical_sound_detected",
        )

    transcript_text, analysis_type, audio_summary, audio_warning = _transcribe_audio_media(
        audio_input
    )
    incident.transcripcion_audio = transcript_text
    return transcript_text, analysis_type, audio_summary, audio_warning


def _record_triage_failure_event(
    *,
    db: Session,
    current_user: Usuario,
    incident: Incidente,
    description: str,
    reason: str,
    ip_origen: str | None,
    user_agent: str | None,
) -> None:
    db.add(
        _create_bitacora_event(
            user=current_user,
            incident=incident,
            accion="TRIAJE_EJECUCION_FALLIDA",
            tipo_evento="TRIAJE",
            descripcion=description,
            datos_nuevos={"reason": reason, "estado": incident.estado},
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    db.commit()


def _log_triage_provider_failure(
    *,
    incident: Incidente,
    error: Exception,
) -> None:
    image_count = sum(1 for item in incident.evidencias if item.tipo_evidencia == "IMAGEN")
    audio_included = any(item.tipo_evidencia == "AUDIO" for item in incident.evidencias)
    provider_name = settings.triage_ai_provider
    model_name = settings.triage_ai_model
    http_status_code = None
    provider_response_excerpt = None

    if isinstance(error, TriageProviderError):
        provider_name = error.provider_name or provider_name
        model_name = error.model_name or model_name
        image_count = error.image_count if error.image_count is not None else image_count
        audio_included = (
            error.audio_included if error.audio_included is not None else audio_included
        )
        http_status_code = error.http_status_code
        provider_response_excerpt = error.provider_response_excerpt

    logger.warning(
        "Triage provider failure: incident_id=%s exception=%s provider=%s model=%s image_count=%s audio_included=%s http_status_code=%s provider_response=%s",
        incident.id_incidente,
        error.__class__.__name__,
        provider_name,
        model_name,
        image_count,
        audio_included,
        http_status_code,
        provider_response_excerpt,
    )


def _build_triage_provider_http_detail(error: TriageProviderError) -> str:
    if error.http_status_code == 400:
        return "Triage AI provider rejected the request payload."
    if error.http_status_code == 401:
        return "Triage AI provider rejected the configured credentials."
    if error.http_status_code == 403:
        response_excerpt = (error.provider_response_excerpt or "").lower()
        if "1010" in response_excerpt or "cloudflare" in response_excerpt:
            return "Triage AI provider blocked the request. Check API key, network, or client headers."
        return "Triage AI provider denied access for the configured project or API key."
    if error.http_status_code == 404:
        return "Triage AI provider model was not found."
    if error.http_status_code == 429:
        return "Triage AI provider quota is exhausted or billing is unavailable."
    if error.http_status_code is not None and error.http_status_code >= 500:
        return "Triage AI provider is temporarily unavailable."
    return "Triage AI provider failed."


def _map_detected_specialty(
    *,
    specialty_map: dict[str, Especialidad],
    raw_name: str | None,
) -> Especialidad | None:
    normalized_name = _normalize_catalog_name(raw_name)
    if normalized_name is None:
        return None
    return specialty_map.get(normalized_name)


def _get_catalog_specialty(
    specialty_map: dict[str, Especialidad],
    *names: str,
) -> Especialidad | None:
    for name in names:
        specialty = specialty_map.get(_normalize_catalog_name(name))
        if specialty is not None:
            return specialty
    return None


def _text_contains_any(value: str | None, markers: Sequence[str]) -> bool:
    if value is None:
        return False
    return any(marker in value for marker in markers)


def _select_visual_specialty_override(
    *,
    specialty_map: dict[str, Especialidad],
    visual_evidence_tags: Sequence[str],
    description: str,
) -> tuple[Especialidad | None, bool]:
    normalized_tags = " ".join(
        item
        for tag in visual_evidence_tags
        if (item := _normalize_catalog_name(tag))
    )
    normalized_description = _normalize_catalog_name(description)

    if _text_contains_any(
        normalized_tags,
        (
            "FLAT TIRE",
            "TIRE",
            "WHEEL",
            "PINCHAZO",
            "LLANTA",
            "LLANTA BAJA",
            "NEUMATICO",
            "RUEDA",
        ),
    ):
        return _get_catalog_specialty(specialty_map, "Llantas"), True

    battery_visual_signal = _text_contains_any(
        normalized_tags,
        (
            "BATTERY",
            "BATERIA",
            "ENGINE BAY",
            "HOOD OPEN",
            "CAPOT",
            "COFRE",
            "MOTOR",
            "BORNE",
            "NO START",
            "ARRANQUE",
        ),
    )
    no_start_description = _text_contains_any(
        normalized_description,
        (
            "NO PRENDE",
            "NO ENCIENDE",
            "NO ARRANCA",
            "NO AVANZA",
            "SE APAGO",
            "SE PARO",
            "ME PARO",
        ),
    )
    if battery_visual_signal and no_start_description:
        return _get_catalog_specialty(specialty_map, "BATERIA", "Electricidad"), False

    if _text_contains_any(
        normalized_tags,
        (
            "TOW",
            "GRUA",
            "CRASH",
            "CHOQUE",
            "COLLISION",
            "IMMOBILE",
            "INMOVIL",
            "ACCIDENTE",
        ),
    ):
        return _get_catalog_specialty(
            specialty_map,
            "GRUA",
            "MECANICA_GENERAL",
            "Mecánica",
        ), False

    return None, False


def _select_reported_specialty_fallback(incident: Incidente) -> Especialidad | None:
    reported = incident.especialidad_reportada_cliente
    if reported is None:
        return None
    normalized = _normalize_catalog_name(reported.nombre)
    if normalized in {
        None,
        "DIAGNOSTICO GENERAL",
        "MECANICA GENERAL",
        "MECANICA",
    }:
        return None
    return reported


def _is_general_detected_specialty(
    *,
    detected_specialty: Especialidad | None,
    raw_detected_specialty: str | None,
) -> bool:
    normalized_mapped = _normalize_catalog_name(
        detected_specialty.nombre if detected_specialty is not None else None
    )
    normalized_raw = _normalize_catalog_name(raw_detected_specialty)
    return "DIAGNOSTICO GENERAL" in {normalized_mapped, normalized_raw}


def _is_generic_ai_text(value: str | None) -> bool:
    normalized = _normalize_catalog_name(value)
    if normalized is None:
        return True
    return _text_contains_any(
        normalized,
        (
            "INFORMACION NO PERMITE",
            "NO PERMITE IDENTIFICAR",
            "FALLA ESPECIFICA",
            "DIAGNOSTICO GENERAL",
            "REVISION GENERAL",
        ),
    )


def _dedupe_reasons(reasons: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        normalized = reason.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _append_operator_note(current: str | None, note: str) -> str:
    current_text = (current or "").strip()
    if not current_text:
        return note
    if note in current_text:
        return current_text
    return f"{current_text} {note}"


def _execute_incident_classification(
    *,
    incident: Incidente,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> IncidentClassificationResponse:
    if incident.estado not in TRIAGE_ELIGIBLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident is not eligible for triage.",
        )

    previous_state = incident.estado
    specialties, specialty_map = _get_specialty_catalog(db)
    specialty_names = [item.nombre for item in specialties]
    images, audio_input = _load_incident_media_inputs(incident)
    (
        audio_transcript,
        audio_analysis_type,
        audio_summary,
        audio_warning,
    ) = _resolve_incident_audio_context(
        incident=incident,
        audio_input=audio_input,
    )
    provider_result, provider_metadata = run_multimodal_triage(
        description=incident.descripcion_cliente,
        reported_specialty_name=incident.especialidad_reportada_cliente.nombre,
        specialty_names=specialty_names,
        images=images,
        audio=audio_input,
        audio_transcript=audio_transcript,
        audio_analysis_type=audio_analysis_type,
        audio_warning=audio_warning,
    )
    provider_metadata["manual_review_confidence_threshold"] = (
        settings.manual_review_confidence_threshold
    )

    detected_specialty = _map_detected_specialty(
        specialty_map=specialty_map,
        raw_name=provider_result.detected_specialty,
    )
    confidence_value = Decimal(provider_result.confidence)
    specialty_override_reason: str | None = None
    suppress_manual_review_reasons: set[str] | None = None
    if _is_general_detected_specialty(
        detected_specialty=detected_specialty,
        raw_detected_specialty=provider_result.detected_specialty,
    ):
        visual_override, suppress_vague_review = _select_visual_specialty_override(
            specialty_map=specialty_map,
            visual_evidence_tags=provider_result.visual_evidence_tags,
            description=incident.descripcion_cliente,
        )
        if visual_override is not None:
            detected_specialty = visual_override
            specialty_override_reason = "visual_evidence_tags"
            provider_metadata["specialty_override_reason"] = specialty_override_reason
            if _normalize_catalog_name(visual_override.nombre) == "LLANTAS":
                confidence_value = max(confidence_value, Decimal("75"))
            if suppress_vague_review:
                suppress_manual_review_reasons = {
                    "low_confidence",
                    "provider_requested_review",
                    "vague_description",
                }
        else:
            reported_override = _select_reported_specialty_fallback(incident)
            if reported_override is not None:
                detected_specialty = reported_override
                specialty_override_reason = "client_reported_specialty"
                provider_metadata["specialty_override_reason"] = specialty_override_reason

    provider_metadata["mapped_detected_specialty"] = (
        detected_specialty.nombre if detected_specialty is not None else None
    )
    provider_metadata["raw_detected_specialty"] = provider_result.detected_specialty
    summary = provider_result.summary
    specific_diagnosis = provider_result.specific_diagnosis
    suggested_service = provider_result.suggested_service
    customer_recommendation = provider_result.customer_recommendation
    operator_notes = provider_result.operator_notes
    if specialty_override_reason is not None:
        if _is_generic_ai_text(summary):
            summary = None
        if _is_generic_ai_text(specific_diagnosis):
            specific_diagnosis = None
        if _is_generic_ai_text(suggested_service):
            suggested_service = None
        if _is_generic_ai_text(customer_recommendation):
            customer_recommendation = None
        if _is_generic_ai_text(operator_notes):
            operator_notes = None

    triage_details = build_triage_details_from_ai_result(
        description=incident.descripcion_cliente,
        detected_specialty_name=(
            detected_specialty.nombre if detected_specialty is not None else None
        ),
        raw_detected_specialty_name=provider_result.detected_specialty,
        severity=provider_result.severity,
        confidence=confidence_value,
        summary=summary,
        specific_diagnosis=specific_diagnosis,
        suggested_service=suggested_service,
        customer_recommendation=customer_recommendation,
        operator_notes=operator_notes,
        visual_evidence_tags=provider_result.visual_evidence_tags,
        provider_requires_manual_review=provider_result.requires_manual_review,
        min_confidence=settings.triage_min_confidence,
        manual_review_confidence_threshold=settings.manual_review_confidence_threshold,
        image_count=len(images),
        audio_summary=provider_result.audio_summary or audio_summary,
        audio_analysis_type=provider_result.audio_analysis_type or audio_analysis_type,
        specialty_override_reason=specialty_override_reason,
        suppress_manual_review_reasons=suppress_manual_review_reasons,
    )
    if (
        (provider_metadata.get("image_count_received_by_backend") or 0) > 0
        and (provider_metadata.get("image_count_sent_to_ai") or 0) == 0
    ):
        triage_details = replace(
            triage_details,
            requires_manual_review=True,
            manual_review_reasons=_dedupe_reasons(
                [*triage_details.manual_review_reasons, "image_not_sent_to_ai"]
            ),
            operator_notes=_append_operator_note(
                triage_details.operator_notes,
                "El cliente adjunto imagenes, pero no pudieron ser analizadas automaticamente por el modelo configurado.",
            ),
        )
    manual_review_required = triage_details.requires_manual_review

    incident.diagnostico_ia_resumen = triage_details.summary
    incident.diagnostico_ia_json = build_triage_payload(
        raw_provider_result=provider_result.model_dump(mode="json"),
        provider_metadata=provider_metadata,
        details=triage_details,
        min_confidence=settings.triage_min_confidence,
    )
    incident.confianza_ia = confidence_value
    incident.transcripcion_audio = audio_transcript
    incident.etiquetas_imagen = triage_details.visual_evidence_tags or None
    incident.severidad = triage_details.severity
    incident.fecha_triaje = utc_now()
    incident.id_especialidad_detectada = (
        detected_specialty.id_especialidad if detected_specialty is not None else None
    )
    incident.requiere_revision_manual = manual_review_required
    incident.estado = "DIAGNOSTICADO" if detected_specialty is not None else "EN_TRIAJE"

    db.add(
        _create_bitacora_event(
            user=current_user,
            incident=incident,
            accion="TRIAJE_EJECUTADO",
            tipo_evento="TRIAJE",
            descripcion="Se ejecuto el triaje cognitivo multimodal del incidente.",
            datos_nuevos={
                "previous_state": previous_state,
                "provider": provider_metadata.get("provider"),
                "model": provider_metadata.get("model"),
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    db.add(
        _create_bitacora_event(
            user=current_user,
            incident=incident,
            accion="TRIAJE_RESULTADO_GUARDADO",
            tipo_evento="TRIAJE",
            descripcion="Se guardo el resultado estructurado del triaje.",
            datos_nuevos={
                "new_state": incident.estado,
                "severidad": incident.severidad,
                "confianza": str(confidence_value),
                "id_especialidad_detectada": incident.id_especialidad_detectada,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    )
    if manual_review_required:
        db.add(
            _create_bitacora_event(
                user=current_user,
                incident=incident,
                accion="TRIAJE_REVISION_MANUAL",
                tipo_evento="TRIAJE",
                descripcion="El incidente requiere revision manual despues del triaje.",
                datos_nuevos={
                    "confidence": str(confidence_value),
                    "detected_specialty": provider_result.detected_specialty,
                    "manual_review_reasons": triage_details.manual_review_reasons,
                    "audio_omitted_reason": provider_metadata.get("audio_omitted_reason"),
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )

    db.commit()
    db.expire_all()
    refreshed_incident = _get_owned_incident(
        db,
        incident_id=incident.id_incidente,
        cliente_id=current_user.id_persona,
    )
    return _build_incident_classification_response(
        incident=refreshed_incident,
        previous_state=previous_state,
    )


def _auto_run_incident_classification(
    *,
    incident_id: int,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> None:
    try:
        incident = _get_owned_incident(
            db,
            incident_id=incident_id,
            cliente_id=current_user.id_persona,
        )
        _execute_incident_classification(
            incident=incident,
            current_user=current_user,
            db=db,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    except HTTPException as exc:
        incident = _get_owned_incident(
            db,
            incident_id=incident_id,
            cliente_id=current_user.id_persona,
        )
        try:
            _record_triage_failure_event(
                db=db,
                current_user=current_user,
                incident=incident,
                description="El auto-triaje no pudo ejecutarse despues del reporte.",
                reason=str(exc.detail),
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        except SQLAlchemyError:
            db.rollback()
    except (StorageError, TriageProviderError) as exc:
        incident = _get_owned_incident(
            db,
            incident_id=incident_id,
            cliente_id=current_user.id_persona,
        )
        try:
            _record_triage_failure_event(
                db=db,
                current_user=current_user,
                incident=incident,
                description="El auto-triaje fallo por un error de almacenamiento o proveedor.",
                reason=str(exc),
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        except SQLAlchemyError:
            db.rollback()
    except SQLAlchemyError:
        db.rollback()


def list_specialties(db: Session) -> list["SpecialtyResponse"]:
    from .schemas import SpecialtyResponse

    rows = list(
        db.scalars(
            select(Especialidad).order_by(Especialidad.nombre.asc())
        )
    )
    return [
        SpecialtyResponse(
            id_especialidad=item.id_especialidad,
            nombre=item.nombre,
            descripcion=item.descripcion,
            nivel_complejidad=item.nivel_complejidad,
        )
        for item in rows
    ]


def report_incident(
    *,
    payload: IncidentReportCreateData,
    current_user: Usuario,
    db: Session,
    offline_sync: bool,
    audio_file: UploadFile | None,
    image_files: Sequence[UploadFile],
    ip_origen: str | None,
    user_agent: str | None,
) -> IncidentReportResponse:
    cliente_id = current_user.id_persona
    if payload.local_uuid:
        existing_incident = _get_owned_incident_by_local_uuid(
            db,
            cliente_id=cliente_id,
            local_uuid=payload.local_uuid,
        )
        if existing_incident is not None:
            try:
                if _ensure_offline_sync_event(
                    db=db,
                    current_user=current_user,
                    incident=existing_incident,
                    offline_sync=offline_sync,
                    ip_origen=ip_origen,
                    user_agent=user_agent,
                ):
                    db.commit()
            except SQLAlchemyError:
                db.rollback()
            return _build_incident_report_response(
                existing_incident,
                message="Incident already registered.",
            )

    _validate_files(audio_file=audio_file, image_files=image_files)
    normalized_description = _normalize_multiline_text(payload.descripcion_cliente) or ""
    if not normalized_description and not image_files and audio_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agrega una descripcion, una foto o un audio para reportar el incidente.",
        )
    storage = get_triage_storage()
    stored_media: list[StoredMedia] = []

    try:
        _get_owned_vehicle(db, vehicle_id=payload.id_vehiculo, cliente_id=cliente_id)
        specialty = _get_specialty(db, payload.id_especialidad_reportada_cliente)

        incident = Incidente(
            id_cliente=cliente_id,
            id_vehiculo=payload.id_vehiculo,
            id_especialidad_reportada_cliente=payload.id_especialidad_reportada_cliente,
            descripcion_cliente=normalized_description,
            latitud=payload.latitud,
            longitud=payload.longitud,
            local_uuid=payload.local_uuid,
            estado="REPORTADO",
        )
        db.add(incident)
        db.flush()

        evidences: list[Evidencia] = []
        for image in image_files:
            stored = storage.save_incident_file(
                incident_id=incident.id_incidente,
                folder="imagenes",
                upload=image,
            )
            stored_media.append(stored)
            evidence = Evidencia(
                tipo_evidencia="IMAGEN",
                categoria="INCIDENTE",
                url_archivo=stored.locator,
                mime_type=stored.mime_type,
                tamano_bytes=stored.size_bytes,
                id_incidente=incident.id_incidente,
            )
            db.add(evidence)
            evidences.append(evidence)

        if audio_file is not None:
            stored = storage.save_incident_file(
                incident_id=incident.id_incidente,
                folder="audio",
                upload=audio_file,
            )
            stored_media.append(stored)
            evidence = Evidencia(
                tipo_evidencia="AUDIO",
                categoria="INCIDENTE",
                url_archivo=stored.locator,
                mime_type=stored.mime_type,
                tamano_bytes=stored.size_bytes,
                id_incidente=incident.id_incidente,
            )
            db.add(evidence)
            evidences.append(evidence)
            try:
                audio_bytes = stored.absolute_path.read_bytes()
            except OSError as exc:
                raise StorageError("Stored audio file could not be read.") from exc
            audio_media_input = AIMediaInput(
                content_bytes=audio_bytes,
                mime_type=stored.mime_type or "application/octet-stream",
                locator=stored.locator,
            )
            (
                incident.transcripcion_audio,
                _audio_analysis_type,
                _audio_summary,
                _audio_warning,
            ) = _transcribe_audio_media(audio_media_input)

        incident.estado = "EN_TRIAJE"

        db.add(
            _create_bitacora_event(
                user=current_user,
                incident=incident,
                accion="INCIDENTE_REPORTADO",
                tipo_evento="CREACION",
                descripcion="Cliente reporto un incidente vehicular.",
                datos_nuevos={
                    "estado": "REPORTADO",
                    "id_vehiculo": payload.id_vehiculo,
                    "id_especialidad_reportada_cliente": specialty.id_especialidad,
                    "latitud": str(payload.latitud),
                    "longitud": str(payload.longitud),
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )

        if evidences:
            db.add(
                _create_bitacora_event(
                    user=current_user,
                    incident=incident,
                    accion="EVIDENCIAS_REGISTRADAS",
                    tipo_evento="EVIDENCIA",
                    descripcion="Se registraron evidencias multimedia para el incidente.",
                    datos_nuevos={
                        "total_evidencias": len(evidences),
                        "imagenes": sum(1 for item in evidences if item.tipo_evidencia == "IMAGEN"),
                        "audio": sum(1 for item in evidences if item.tipo_evidencia == "AUDIO"),
                    },
                    ip_origen=ip_origen,
                    user_agent=user_agent,
                )
            )

        db.add(
            _create_bitacora_event(
                user=current_user,
                incident=incident,
                accion="INCIDENTE_EN_TRIAJE",
                tipo_evento="TRIAJE",
                descripcion="Incidente enviado a la etapa de triaje.",
                datos_nuevos={
                    "estado": "EN_TRIAJE",
                    "triage_ready": True,
                },
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        )

        _ensure_offline_sync_event(
            db=db,
            current_user=current_user,
            incident=incident,
            offline_sync=offline_sync,
            ip_origen=ip_origen,
            user_agent=user_agent,
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
            detail="Incident files could not be stored.",
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        storage.delete_many(stored_media)
        if payload.local_uuid:
            existing_incident = _get_owned_incident_by_local_uuid(
                db,
                cliente_id=cliente_id,
                local_uuid=payload.local_uuid,
            )
            if existing_incident is not None:
                try:
                    if _ensure_offline_sync_event(
                        db=db,
                        current_user=current_user,
                        incident=existing_incident,
                        offline_sync=offline_sync,
                        ip_origen=ip_origen,
                        user_agent=user_agent,
                    ):
                        db.commit()
                except SQLAlchemyError:
                    db.rollback()
                return _build_incident_report_response(
                    existing_incident,
                    message="Incident already registered.",
                )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        storage.delete_many(stored_media)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Incident could not be created.",
        ) from exc

    if settings.triage_auto_run_after_report:
        _auto_run_incident_classification(
            incident_id=incident.id_incidente,
            current_user=current_user,
            db=db,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )

    created_incident = _get_owned_incident(
        db,
        incident_id=incident.id_incidente,
        cliente_id=cliente_id,
    )
    return _build_incident_report_response(
        created_incident,
        message="Incident created and sent to triage.",
    )


def get_incident_detail(
    *,
    incident_id: int,
    current_user: Usuario,
    db: Session,
) -> IncidentDetailResponse:
    incident = _get_owned_incident(
        db,
        incident_id=incident_id,
        cliente_id=current_user.id_persona,
    )
    return _build_incident_detail_response(incident)


def classify_incident(
    *,
    incident_id: int,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> IncidentClassificationResponse:
    incident = _get_owned_incident(
        db,
        incident_id=incident_id,
        cliente_id=current_user.id_persona,
    )

    try:
        return _execute_incident_classification(
            incident=incident,
            current_user=current_user,
            db=db,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
    except TriageProviderNotConfiguredError as exc:
        _log_triage_provider_failure(incident=incident, error=exc)
        try:
            _record_triage_failure_event(
                db=db,
                current_user=current_user,
                incident=incident,
                description="No se pudo ejecutar el triaje porque el proveedor no esta configurado.",
                reason=str(exc),
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        except SQLAlchemyError:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Triage AI provider is not configured.",
        ) from exc
    except TriageProviderInvalidResponseError as exc:
        _log_triage_provider_failure(incident=incident, error=exc)
        try:
            _record_triage_failure_event(
                db=db,
                current_user=current_user,
                incident=incident,
                description="El proveedor devolvio una respuesta de triaje invalida.",
                reason=str(exc),
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        except SQLAlchemyError:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Triage AI returned an invalid response.",
        ) from exc
    except TriageProviderError as exc:
        _log_triage_provider_failure(incident=incident, error=exc)
        try:
            _record_triage_failure_event(
                db=db,
                current_user=current_user,
                incident=incident,
                description="El proveedor de triaje fallo durante la clasificacion.",
                reason=str(exc),
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        except SQLAlchemyError:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_build_triage_provider_http_detail(exc),
        ) from exc
    except StorageError as exc:
        try:
            _record_triage_failure_event(
                db=db,
                current_user=current_user,
                incident=incident,
                description="No se pudieron cargar las evidencias almacenadas para el triaje.",
                reason=str(exc),
                ip_origen=ip_origen,
                user_agent=user_agent,
            )
        except SQLAlchemyError:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Incident evidences could not be loaded for triage.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Incident triage could not be persisted.",
        ) from exc


def matchmake_incident(
    *,
    incident_id: int,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> MatchmakingSelectionResponse:
    incident = _get_owned_incident(
        db,
        incident_id=incident_id,
        cliente_id=current_user.id_persona,
    )
    return _execute_incident_matchmaking(
        incident=incident,
        current_user=current_user,
        no_candidate_notify_user=current_user,
        db=db,
        ip_origen=ip_origen,
        user_agent=user_agent,
    )


def rematch_incident_after_workshop_rejection(
    *,
    incident: Incidente,
    current_user: Usuario,
    client_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> MatchmakingSelectionResponse:
    return _execute_incident_matchmaking(
        incident=incident,
        current_user=current_user,
        no_candidate_notify_user=client_user,
        db=db,
        ip_origen=ip_origen,
        user_agent=user_agent,
    )


def get_matchmaking_status(
    *,
    incident_id: int,
    current_user: Usuario,
    db: Session,
) -> MatchmakingStatusResponse:
    incident = _get_owned_incident(
        db,
        incident_id=incident_id,
        cliente_id=current_user.id_persona,
    )
    active_request = _get_active_matchmaking_request(db, incident_id=incident.id_incidente)
    now = utc_now()
    active_request_response = (
        _build_matchmaking_active_request_response(
            active_request,
            incident=incident,
            is_expired=_is_request_expired(active_request, now=now),
        )
        if active_request is not None
        else None
    )
    message = (
        "Active matchmaking request found."
        if active_request_response is not None
        else "No active matchmaking request."
    )
    return MatchmakingStatusResponse(
        incident_id=incident.id_incidente,
        incident_state=incident.estado,
        detected_specialty=_build_specialty_summary(incident.especialidad_detectada),
        severity=incident.severidad,
        active_request=active_request_response,
        message=message,
    )


def list_operario_assigned_services(
    *,
    current_user: Usuario,
    db: Session,
) -> list[OperarioAssignedServiceSummary]:
    services = list(
        db.scalars(
            _build_operario_service_query()
            .where(Servicio.id_persona_operario == current_user.id_persona)
            .order_by(
                Servicio.fecha_asignacion_operario.desc().nullslast(),
                Servicio.id_servicio.desc(),
            )
        )
    )
    return [_build_operario_assigned_service_summary(item) for item in services]


def get_operario_structured_profile(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> OperarioStructuredProfileResponse:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    _validate_structured_profile_ready(service)
    return _build_operario_structured_profile_response(service)


def acknowledge_operario_structured_profile(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
    ip_origen: str | None,
    user_agent: str | None,
) -> StructuredProfileAcknowledgeResponse:
    service = _get_assigned_service(
        db,
        service_id=service_id,
        operario_id=current_user.id_persona,
    )
    incident = _validate_structured_profile_ready(service)

    db.add(
        Bitacora(
            accion="PERFIL_FALLA_ESTRUCTURADO_ACK",
            tipo_evento="TRIAJE",
            descripcion="El operario confirmo la lectura del perfil de falla estructurado por IA.",
            entidad_principal="SERVICIO",
            id_entidad_principal=service.id_servicio,
            datos_nuevos={
                "service_id": service.id_servicio,
                "incident_id": incident.id_incidente,
                "service_state": service.estado,
            },
            ip_origen=ip_origen,
            user_agent=user_agent,
            hash_evento="",
            id_usuario=current_user.id_usuario,
            id_incidente=incident.id_incidente,
            id_solicitud=service.id_solicitud,
            id_servicio=service.id_servicio,
        )
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Structured profile acknowledgment could not be persisted.",
        ) from exc

    return StructuredProfileAcknowledgeResponse(
        status="ok",
        service_id=service.id_servicio,
        service_state=service.estado,
        message="Structured profile acknowledged successfully.",
    )
