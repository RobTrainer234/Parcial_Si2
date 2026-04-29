from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _NormalizedModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class IncidentReportCreateData(_NormalizedModel):
    id_vehiculo: int
    latitud: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    longitud: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))
    descripcion_cliente: str = Field(min_length=1, max_length=5000)
    id_especialidad_reportada_cliente: int

    @field_validator("descripcion_cliente")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("descripcion_cliente must not be empty.")
        return normalized


class IncidentEvidenceResponse(BaseModel):
    id_evidencia: int
    tipo_evidencia: str
    categoria: str
    url_archivo: str
    mime_type: str | None = None
    tamano_bytes: int | None = None
    fecha_registro: datetime


class SpecialtySummaryResponse(BaseModel):
    id_especialidad: int
    nombre: str


class SpecialtyResponse(BaseModel):
    id_especialidad: int
    nombre: str
    descripcion: str | None = None
    nivel_complejidad: int | None = None


class IncidentEvidenceSummaryResponse(BaseModel):
    total: int
    imagenes: int
    audio: int


class IncidentReportResponse(BaseModel):
    incident_id: int
    status: str
    message: str
    id_vehiculo: int
    latitud: Decimal
    longitud: Decimal
    descripcion_cliente: str
    especialidad_reportada: SpecialtySummaryResponse
    evidence_summary: IncidentEvidenceSummaryResponse
    evidences: list[IncidentEvidenceResponse]
    fecha_hora: datetime


class IncidentDetailResponse(BaseModel):
    incident_id: int
    status: str
    fecha_hora: datetime
    latitud: Decimal
    longitud: Decimal
    descripcion_cliente: str
    id_vehiculo: int
    especialidad_reportada: SpecialtySummaryResponse
    especialidad_detectada: SpecialtySummaryResponse | None = None
    diagnostico_ia_resumen: str | None = None
    diagnostico_ia_json: dict[str, Any] | None = None
    confianza_ia: Decimal | None = None
    transcripcion_audio: str | None = None
    etiquetas_imagen: Any | None = None
    fecha_triaje: datetime | None = None
    requiere_revision_manual: bool
    evidences: list[IncidentEvidenceResponse]
    evidence_summary: IncidentEvidenceSummaryResponse


class IncidentClassificationResponse(BaseModel):
    incident_id: int
    previous_state: str
    new_state: str
    reported_specialty: SpecialtySummaryResponse
    detected_specialty: SpecialtySummaryResponse | None = None
    severity: str | None = None
    confidence: Decimal | None = None
    requires_manual_review: bool
    summary: str | None = None


class WorkshopCandidateSummary(BaseModel):
    id_taller: int
    nombre_comercial: str
    reputacion_prom: Decimal | None = None
    radio_accion_km: Decimal
    distance_km: Decimal


class MatchmakingActiveRequestResponse(BaseModel):
    request_id: int
    request_status: str
    attempt_number: int
    expires_at: datetime
    used_insurance_priority: bool
    score_proximidad: Decimal | None = None
    score_reputacion: Decimal | None = None
    score_total: Decimal | None = None
    selected_workshop: WorkshopCandidateSummary
    is_expired: bool


class MatchmakingSelectionResponse(BaseModel):
    incident_id: int
    previous_state: str
    new_state: str
    detected_specialty: SpecialtySummaryResponse
    severity: str
    selected_workshop: WorkshopCandidateSummary | None = None
    used_insurance_priority: bool | None = None
    request_id: int | None = None
    request_status: str | None = None
    expires_at: datetime | None = None
    score_proximidad: Decimal | None = None
    score_reputacion: Decimal | None = None
    score_total: Decimal | None = None
    distance_km: Decimal | None = None
    attempt_number: int | None = None
    no_candidate: bool
    message: str


class MatchmakingStatusResponse(BaseModel):
    incident_id: int
    incident_state: str
    detected_specialty: SpecialtySummaryResponse | None = None
    severity: str | None = None
    active_request: MatchmakingActiveRequestResponse | None = None
    message: str


class OperarioAssignedServiceSummary(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    detected_specialty: SpecialtySummaryResponse | None = None
    severity: str | None = None
    ai_summary: str | None = None
    prequotation_code: str | None = None
    prequotation_min: Decimal | None = None
    prequotation_max: Decimal | None = None
    prequotation_currency: str | None = "BOB"


class OperarioServiceWorkshopSummary(BaseModel):
    id_taller: int
    nombre_comercial: str


class OperarioStructuredProfileResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    latitud: Decimal
    longitud: Decimal
    workshop: OperarioServiceWorkshopSummary | None = None
    client_reported_specialty: SpecialtySummaryResponse | None = None
    detected_specialty: SpecialtySummaryResponse | None = None
    severity: str | None = None
    confidence: Decimal | None = None
    ai_summary: str | None = None
    transcripcion_audio: str | None = None
    etiquetas_imagen: Any | None = None
    herramientas_sugeridas: list[str] | None = None
    requiere_grua: bool | None = None
    observaciones: str | None = None
    prequotation_code: str | None = None
    prequotation_min: Decimal | None = None
    prequotation_max: Decimal | None = None
    prequotation_currency: str | None = "BOB"
    requiere_revision_manual: bool
    diagnostico_ia_json: dict[str, Any] | None = None
    evidence_summary: IncidentEvidenceSummaryResponse
    evidences: list[IncidentEvidenceResponse]


class StructuredProfileAcknowledgeResponse(BaseModel):
    status: str
    service_id: int
    service_state: str
    message: str
