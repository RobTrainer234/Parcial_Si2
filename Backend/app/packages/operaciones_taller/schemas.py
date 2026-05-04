from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.config import settings


class _NormalizedModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class WorkshopSummaryResponse(BaseModel):
    id_taller: int
    nombre_comercial: str


class SpecialtySummaryResponse(BaseModel):
    id_especialidad: int
    nombre: str


class WorkshopRequestSummary(BaseModel):
    request_id: int
    incident_id: int
    incident_state: str
    sent_at: datetime
    expires_at: datetime
    distance_km: Decimal
    detected_specialty: SpecialtySummaryResponse | None = None
    severity: str | None = None
    ai_summary: str | None = None
    used_insurance_priority: bool
    attempt_number: int
    score_total: Decimal | None = None
    request_status: str


class WorkshopRequestDetailResponse(BaseModel):
    request_id: int
    request_status: str
    incident_id: int
    incident_state: str
    workshop: WorkshopSummaryResponse
    sent_at: datetime
    expires_at: datetime
    is_expired: bool
    distance_km: Decimal
    used_insurance_priority: bool
    attempt_number: int
    score_proximidad: Decimal | None = None
    score_reputacion: Decimal | None = None
    score_total: Decimal | None = None
    incident_latitud: Decimal
    incident_longitud: Decimal
    client_reported_specialty: SpecialtySummaryResponse | None = None
    detected_specialty: SpecialtySummaryResponse | None = None
    severity: str | None = None
    ai_summary: str | None = None
    specific_diagnosis: str | None = None
    suggested_service: str | None = None
    customer_recommendation: str | None = None
    operator_notes: str | None = None
    visual_evidence_tags: list[str] = Field(default_factory=list)
    transcripcion_audio: str | None = None
    image_labels: list[str] | dict[str, object] | None = None
    service_id: int | None = None
    service_state: str | None = None
    prequotation_code: str | None = None
    prequotation_min: Decimal | None = None
    prequotation_max: Decimal | None = None
    prequotation_currency: str | None = "BOB"
    catalog_service_name: str | None = None
    motivo_cierre: str | None = None


class WorkshopRequestDecisionRequest(_NormalizedModel):
    decision: str
    motivo: str | None = Field(default=None, max_length=200)

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"ACEPTAR", "RECHAZAR"}:
            raise ValueError("decision must be ACEPTAR or RECHAZAR.")
        return normalized

    @model_validator(mode="after")
    def validate_reason(self) -> "WorkshopRequestDecisionRequest":
        if self.decision == "RECHAZAR" and not self.motivo:
            raise ValueError("motivo is required when rejecting a request.")
        return self


class WorkshopRequestDecisionResponse(BaseModel):
    request_id: int
    request_status: str
    incident_id: int
    incident_new_state: str
    workshop: WorkshopSummaryResponse
    service_id: int | None = None
    service_state: str | None = None
    prequotation_code: str | None = None
    prequotation_min: Decimal | None = None
    prequotation_max: Decimal | None = None
    prequotation_currency: str | None = "BOB"
    catalog_service_name: str | None = None
    next_request_id: int | None = None
    no_candidate_after_rejection: bool = False
    next_selected_workshop: WorkshopSummaryResponse | None = None
    message: str


class WaitingAssignmentServiceSummary(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    request_id: int
    workshop: WorkshopSummaryResponse
    detected_specialty: SpecialtySummaryResponse | None = None
    severity: str | None = None
    ai_summary: str | None = None
    prequotation_code: str | None = None
    prequotation_min: Decimal | None = None
    prequotation_max: Decimal | None = None
    prequotation_currency: str | None = "BOB"
    catalog_service_name: str | None = None
    assignment_timestamp: datetime | None = None


class WorkshopServiceHistorySummary(BaseModel):
    service_id: int
    request_id: int
    incident_id: int
    service_state: str
    incident_state: str
    specialty: str | None = None
    ai_summary: str | None = None
    client_name: str | None = None
    operario_id: int | None = None
    operario_name: str | None = None
    workshop_name: str
    prequotation_code: str | None = None
    estimated_min: Decimal | None = None
    estimated_max: Decimal | None = None
    final_amount: Decimal | None = None
    payment_status: str | None = None
    rating_average: Decimal | None = None
    rating_comment: str | None = None
    created_at: datetime
    assigned_at: datetime | None = None
    completed_at: datetime | None = None
    paid_at: datetime | None = None


class WorkshopServiceHistoryDetailResponse(WorkshopServiceHistorySummary):
    client_description: str | None = None
    incident_reference: str | None = None
    detected_specialty: str | None = None
    operario_availability: str | None = None
    payment_amount: Decimal | None = None
    payment_currency: str | None = None
    trabajo_realizado: str | None = None
    diagnostico_fisico: str | None = None
    observaciones: str | None = None
    recomendaciones: str | None = None
    final_evidence_count: int = 0


class OperarioCandidateSummary(BaseModel):
    id_persona_operario: int
    nombre_completo: str
    estado_disponibilidad: str
    matched_specialty: SpecialtySummaryResponse
    anios_experiencia: int
    certificacion_url: str | None = None
    recommended: bool
    match_reason: str


class AssignOperarioRequest(_NormalizedModel):
    id_persona_operario: int


class AssignedOperarioSummary(BaseModel):
    id_persona_operario: int
    nombre_completo: str
    estado_disponibilidad: str
    matched_specialty: SpecialtySummaryResponse


class AssignOperarioResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    request_id: int
    assignment_timestamp: datetime | None = None
    assigned_operario: AssignedOperarioSummary
    message: str


class RepairReportItemInput(_NormalizedModel):
    descripcion: str = Field(min_length=1, max_length=150)
    cantidad: Decimal = Field(gt=0)
    costo_unitario: Decimal = Field(ge=0)
    observacion: str | None = Field(default=None, max_length=2000)


class UsedSparePartResponse(BaseModel):
    id_servicio_repuesto: int
    descripcion: str
    cantidad: Decimal
    costo_unitario: Decimal
    subtotal: Decimal
    observacion: str | None = None


class FinalEvidenceResponse(BaseModel):
    id_evidencia: int
    tipo_evidencia: str
    categoria: str
    url_archivo: str
    mime_type: str | None = None
    tamano_bytes: int | None = None
    fecha_registro: datetime


class RepairReportSnapshotResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    report_id: int | None = None
    accion_realizada: str | None = None
    diagnostico_fisico: str | None = None
    observaciones: str | None = None
    recomendaciones: str | None = None
    total_additional_cost: Decimal
    used_items: list[UsedSparePartResponse]
    final_evidences: list[FinalEvidenceResponse]
    saved_at: datetime | None = None


class RepairReportSaveResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    report_id: int
    accion_realizada: str
    diagnostico_fisico: str | None = None
    observaciones: str | None = None
    recomendaciones: str | None = None
    total_additional_cost: Decimal
    used_items: list[UsedSparePartResponse]
    final_evidences: list[FinalEvidenceResponse]
    saved_at: datetime
    message: str


class StaffSpecialtyResponse(BaseModel):
    id_especialidad: int
    nombre: str
    anios_experiencia: int
    certificacion_url: str | None = None


class WorkshopStaffSummary(BaseModel):
    operario_id: int
    persona_id: int
    nombre_completo: str
    ci: str
    email: EmailStr
    telefono: str | None = None
    estado_disponibilidad: str
    activo: bool
    specialties: list[StaffSpecialtyResponse]
    registered_at: datetime | None = None


class StaffCreateSpecialtyInput(_NormalizedModel):
    id_especialidad: int
    anios_experiencia: int = Field(default=0, ge=0)
    certificacion_url: str | None = Field(default=None, max_length=2000)


class WorkshopStaffCreateRequest(_NormalizedModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    ci: str = Field(min_length=1, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    telefono: str | None = Field(default=None, min_length=1, max_length=20)
    direccion: str | None = Field(default=None, max_length=2000)
    specialties: list[StaffCreateSpecialtyInput] = Field(default_factory=list, min_length=1)


class WorkshopStaffAvailabilityUpdateRequest(_NormalizedModel):
    new_status: str
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("new_status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.upper()


class WorkshopConfiguredSpecialtyResponse(BaseModel):
    id_especialidad: int
    nombre: str
    activo: bool


class WorkshopCatalogServiceCreateRequest(_NormalizedModel):
    id_especialidad: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=5000)
    precio_base_min: Decimal = Field(ge=0)
    precio_base_max: Decimal = Field(ge=0)
    incluye_repuestos_basicos: bool

    @field_validator("nombre")
    @classmethod
    def normalize_nombre(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("nombre must not be empty.")
        return normalized

    @model_validator(mode="after")
    def validate_price_range(self) -> "WorkshopCatalogServiceCreateRequest":
        if self.precio_base_max < self.precio_base_min:
            raise ValueError("precio_base_max must be greater than or equal to precio_base_min.")
        return self


class WorkshopCatalogServiceUpdateRequest(_NormalizedModel):
    id_especialidad: int | None = Field(default=None, gt=0)
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=5000)
    precio_base_min: Decimal | None = Field(default=None, ge=0)
    precio_base_max: Decimal | None = Field(default=None, ge=0)
    incluye_repuestos_basicos: bool | None = None
    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def normalize_optional_nombre(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("nombre must not be empty.")
        return normalized

    @model_validator(mode="after")
    def validate_update_payload(self) -> "WorkshopCatalogServiceUpdateRequest":
        meaningful_values = (
            self.id_especialidad,
            self.nombre,
            self.descripcion,
            self.precio_base_min,
            self.precio_base_max,
            self.incluye_repuestos_basicos,
            self.activo,
        )
        if all(value is None for value in meaningful_values):
            raise ValueError("At least one field must be provided for update.")
        if (
            self.precio_base_min is not None
            and self.precio_base_max is not None
            and self.precio_base_max < self.precio_base_min
        ):
            raise ValueError("precio_base_max must be greater than or equal to precio_base_min.")
        return self


class WorkshopCatalogServiceResponse(BaseModel):
    catalog_id: int
    workshop_id: int
    id_especialidad: int
    especialidad_nombre: str
    nombre: str
    descripcion: str | None = None
    precio_base_min: Decimal
    precio_base_max: Decimal
    incluye_repuestos_basicos: bool
    activo: bool


class WorkshopMediaFileResponse(BaseModel):
    id_taller_archivo: int
    tipo_archivo: str
    nombre_archivo: str
    url_archivo: str
    mime_type: str | None = None
    tamano_bytes: int | None = None
    fecha_registro: datetime
    descripcion: str | None = None
    activo: bool


class WorkshopProfileResponse(BaseModel):
    workshop_id: int
    nombre_comercial: str
    descripcion: str | None = None
    latitud: Decimal
    longitud: Decimal
    radio_accion_km: Decimal
    activo: bool
    acepta_seguro_propio: bool
    specialties: list[WorkshopConfiguredSpecialtyResponse]
    imagenes_taller: list[WorkshopMediaFileResponse] = Field(default_factory=list)
    certificados_tecnicos: list[WorkshopMediaFileResponse] = Field(default_factory=list)


class WorkshopProfileUpdateRequest(_NormalizedModel):
    nombre_comercial: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=5000)
    latitud: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    longitud: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))
    radio_accion_km: Decimal = Field(gt=0)
    specialty_ids: list[int] = Field(min_length=1)
    acepta_seguro_propio: bool | None = None

    @field_validator("radio_accion_km")
    @classmethod
    def validate_radio_accion_km_platform_limit(cls, value: Decimal) -> Decimal:
        if value > Decimal(str(settings.workshop_max_action_radius_km)):
            raise ValueError("radio_accion_km exceeds the platform maximum allowed radius.")
        return value


class WorkshopMediaUploadRequest(_NormalizedModel):
    tipo_archivo: str
    descripcion: str | None = Field(default=None, max_length=2000)

    @field_validator("tipo_archivo")
    @classmethod
    def normalize_tipo_archivo(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"IMAGEN_TALLER", "CERTIFICADO_TECNICO"}:
            raise ValueError("tipo_archivo must be IMAGEN_TALLER or CERTIFICADO_TECNICO.")
        return normalized


class WorkshopDashboardPeriodResponse(BaseModel):
    date_from: datetime
    date_to: datetime


class DashboardCountItem(BaseModel):
    label: str
    count: int


class DashboardStuckServiceItem(BaseModel):
    service_id: int
    incident_id: int
    current_state: str
    minutes_in_current_state: Decimal | None = None
    client_reported_description: str
    detected_specialty: str | None = None
    severity: str | None = None
    assigned_operario_name: str | None = None
    reason: str


class WorkshopDashboardKpiResponse(BaseModel):
    pending_requests: int
    accepted_requests: int
    rejected_requests: int
    expired_requests: int
    active_services: int
    completed_services: int
    paid_services: int
    pending_payments: int
    total_revenue: Decimal
    average_rating: Decimal | None = None
    first_contact_resolution_rate: Decimal | None = None
    average_acceptance_time_minutes: Decimal | None = None
    average_completion_time_minutes: Decimal | None = None


class WorkshopDashboardOperationsResponse(BaseModel):
    services_by_state: list[DashboardCountItem]
    requests_by_status: list[DashboardCountItem]
    incidents_by_severity: list[DashboardCountItem]
    incidents_by_detected_specialty: list[DashboardCountItem]
    incident_heatmap_points: list["IncidentHeatmapPoint"]
    stuck_services: list[DashboardStuckServiceItem]


class PrequotationDeviationItem(BaseModel):
    service_id: int
    incident_id: int
    prequotation_code: str
    prequotation_min: Decimal
    prequotation_max: Decimal
    final_cost: Decimal
    deviation_amount: Decimal
    deviation_percentage: Decimal
    status: str
    risk_level: str


class WorkshopDashboardFinancialResponse(BaseModel):
    total_revenue: Decimal
    confirmed_payments: int
    pending_payments: int
    rejected_payments: int
    average_ticket: Decimal | None = None
    monthly_revenue: list["MonthlyRevenueItem"]
    projected_revenue: Decimal | None = None
    prequotation_vs_final: list[PrequotationDeviationItem]


class OperarioDashboardItem(BaseModel):
    operario_id: int
    nombre_completo: str
    estado_disponibilidad: str
    assigned_services: int
    completed_services: int
    average_rating: Decimal | None = None
    average_completion_time_minutes: Decimal | None = None
    active_service_id: int | None = None
    risk_flag: str | None = None


class WorkshopDashboardOperarioResponse(BaseModel):
    operarios: list[OperarioDashboardItem]
    operario_ranking: list["OperarioRankingItem"]


class LowRatingServiceItem(BaseModel):
    service_id: int
    incident_id: int
    rating_id: int
    stars: int
    comment: str | None = None
    rated_at: datetime
    rated_target_type: str


class WorkshopDashboardReputationResponse(BaseModel):
    workshop_average_rating: Decimal | None = None
    total_ratings: int
    rating_distribution: list[DashboardCountItem]
    low_rating_services: list[LowRatingServiceItem]


class WorkshopDashboardActionItem(BaseModel):
    priority: str
    type: str
    title: str
    description: str
    related_service_id: int | None = None
    related_incident_id: int | None = None
    recommended_action: str


class MonthlyRevenueItem(BaseModel):
    month: str
    revenue: Decimal


class IncidentHeatmapPoint(BaseModel):
    latitud: Decimal
    longitud: Decimal
    severidad: str | None = None
    especialidad: str | None = None
    cantidad: int


class OperarioRankingItem(BaseModel):
    operario_id: int
    nombre_completo: str
    efficiency_score: Decimal
    completed_services: int
    average_rating: Decimal | None = None
    average_completion_time_minutes: Decimal | None = None


class WorkshopDashboardOverviewResponse(BaseModel):
    period: WorkshopDashboardPeriodResponse
    kpis: WorkshopDashboardKpiResponse
    operations: WorkshopDashboardOperationsResponse
    financial: WorkshopDashboardFinancialResponse
    operarios: WorkshopDashboardOperarioResponse
    reputation: WorkshopDashboardReputationResponse
    action_items: list[WorkshopDashboardActionItem]


WorkshopDashboardOperationsResponse.model_rebuild()
WorkshopDashboardFinancialResponse.model_rebuild()
WorkshopDashboardOperarioResponse.model_rebuild()
