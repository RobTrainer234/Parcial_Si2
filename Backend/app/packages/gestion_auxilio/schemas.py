from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _NormalizedModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class RouteStepSummary(BaseModel):
    distance_meters: Decimal
    duration_seconds: Decimal
    name: str | None = None
    maneuver_type: str | None = None
    maneuver_modifier: str | None = None
    instruction: str | None = None


class NavigationStartRequest(_NormalizedModel):
    latitud_actual: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    longitud_actual: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))
    accuracy_meters: Decimal | None = Field(default=None, ge=0)
    speed_mps: Decimal | None = Field(default=None, ge=0)


class NavigationStartResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    destination_latitud: Decimal
    destination_longitud: Decimal
    origin_latitud: Decimal
    origin_longitud: Decimal
    route_distance_meters: Decimal
    route_duration_seconds: Decimal
    geometry: dict[str, object] | list[object] | str | None = None
    steps: list[RouteStepSummary] = Field(default_factory=list)
    arrival_threshold_meters: int
    location_point_id: int | None = None
    message: str


class ServiceLocationUpdateRequest(_NormalizedModel):
    latitud: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    longitud: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))
    accuracy_meters: Decimal | None = Field(default=None, ge=0)
    heading: Decimal | None = None
    speed_mps: Decimal | None = Field(default=None, ge=0)
    device_timestamp: datetime | None = None


class ServiceLocationUpdateResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    current_distance_meters: Decimal
    arrival_threshold_meters: int
    has_arrived: bool
    location_point_id: int
    message: str


class NavigationStatusResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    destination_latitud: Decimal
    destination_longitud: Decimal
    last_known_latitud: Decimal | None = None
    last_known_longitud: Decimal | None = None
    last_known_at: datetime | None = None
    current_distance_meters: Decimal | None = None
    profile_acknowledged: bool
    has_arrived: bool
    arrival_threshold_meters: int
    message: str


class ServiceProgressHistoryItem(BaseModel):
    timestamp: datetime
    action: str
    previous_state: str | None = None
    new_state: str | None = None
    observacion: str | None = None


class ServiceProgressSnapshotResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    detected_specialty: str | None = None
    ai_summary: str | None = None
    profile_acknowledged: bool
    arrival_recorded: bool
    allowed_next_states: list[str]
    timeline: list[ServiceProgressHistoryItem] = Field(default_factory=list)


class ServiceProgressUpdateRequest(_NormalizedModel):
    new_state: str
    observacion: str | None = Field(default=None, max_length=2000)

    @field_validator("new_state")
    @classmethod
    def normalize_new_state(cls, value: str) -> str:
        return value.upper()


class ServiceProgressUpdateResponse(BaseModel):
    service_id: int
    previous_state: str
    new_state: str
    incident_id: int
    incident_state: str
    changed_at: datetime
    message: str


class FinalizationTimelineItem(BaseModel):
    timestamp: datetime
    action: str
    previous_state: str | None = None
    new_state: str | None = None
    motivo: str | None = None
    duration_seconds: int | None = None


class FinalizationStatusResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    report_exists: bool
    final_evidence_count: int
    finalization_eligible: bool
    client_decision_pending: bool
    confirmed_at: datetime | None = None
    timeline: list[FinalizationTimelineItem] = Field(default_factory=list)


class FinalizationRequestResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    client_decision_pending: bool
    final_evidence_count: int
    requested_at: datetime
    message: str


class FinalizationDecisionRequest(_NormalizedModel):
    decision: str
    motivo: str | None = Field(default=None, max_length=2000)

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CONFIRMAR", "RECHAZAR"}:
            raise ValueError("decision must be CONFIRMAR or RECHAZAR.")
        return normalized

    @model_validator(mode="after")
    def validate_reason(self) -> "FinalizationDecisionRequest":
        if self.decision == "RECHAZAR" and not self.motivo:
            raise ValueError("motivo is required when rejecting finalization.")
        return self


class FinalizationDecisionResponse(BaseModel):
    service_id: int
    previous_state: str
    new_state: str
    incident_id: int
    incident_state: str
    confirmed_at: datetime | None = None
    duration_seconds: int | None = None
    final_evidence_count: int
    message: str


class TrackingHistoryPointResponse(BaseModel):
    latitud: Decimal
    longitud: Decimal
    fecha_hora: datetime


class TrackingStatusResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_latitud: Decimal
    incident_longitud: Decimal
    last_operario_latitud: Decimal | None = None
    last_operario_longitud: Decimal | None = None
    last_location_at: datetime | None = None
    has_live_location: bool
    location_stale: bool
    current_distance_meters: Decimal | None = None
    eta_seconds: int | None = None
    eta_text: str | None = None
    tracking_message: str


class DeviceRegistrationRequest(_NormalizedModel):
    device_token: str = Field(min_length=1, max_length=255)
    platform: str
    notifications_enabled: bool = True

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"ANDROID", "IOS", "WEB"}:
            raise ValueError("platform must be ANDROID, IOS or WEB.")
        return normalized


class DeviceRegistrationResponse(BaseModel):
    device_id: int
    user_id: int
    device_token: str
    platform: str
    active: bool
    registered_at: datetime
    message: str


class DeviceUnregisterRequest(_NormalizedModel):
    device_token: str = Field(min_length=1, max_length=255)


class NotificationInboxItem(BaseModel):
    notification_id: int
    service_id: int | None = None
    request_id: int | None = None
    channel: str
    title: str
    message: str
    payload: dict[str, object] | list[object] | None = None
    status: str
    provider: str | None = None
    created_at: datetime
    sent_at: datetime | None = None
    read_at: datetime | None = None


class NotificationReadResponse(BaseModel):
    notification_id: int
    status: str
    read_at: datetime | None = None
    message: str


class UnreadCountResponse(BaseModel):
    unread_count: int


class DispatchPendingResponse(BaseModel):
    provider: str
    active_device_count: int
    total_pending: int
    dispatched_count: int
    failed_count: int
    skipped_count: int
    message: str


class IncidentDiagnosisSummaryResponse(BaseModel):
    incident_id: int
    incident_state: str
    incident_latitud: Decimal
    incident_longitud: Decimal
    client_reported_specialty: str | None = None
    detected_specialty: str | None = None
    severity: str | None = None
    confidence: Decimal | None = None
    ai_summary: str | None = None
    specific_diagnosis: str | None = None
    suggested_service: str | None = None
    customer_recommendation: str | None = None
    operator_notes: str | None = None
    visual_evidence_tags: list[str] = Field(default_factory=list)
    transcripcion_audio: str | None = None
    etiquetas_imagen: dict[str, object] | list[object] | None = None
    requires_manual_review: bool
    diagnostico_ia_json: dict[str, object] | None = None
    diagnosis_ready: bool


class RecommendedWorkshopResponse(BaseModel):
    workshop_id: int
    workshop_name: str
    latitud: Decimal
    longitud: Decimal
    distance_km: Decimal
    distance_meters: Decimal
    reputation: Decimal | None = None
    specialty_match: bool
    insurance_exists_with_workshop: bool
    insurance_priority_applied: bool
    insurance_covering_this_specialty: bool
    coverage_name: str | None = None
    ranking_score: Decimal | None = None
    estimated_arrival_text: str | None = None
    estimated_cost: Decimal | None = None
    currency: str | None = None
    current_matchmaking_status: str | None = None
    is_top_recommendation: bool


class IncidentRecommendationsResponse(BaseModel):
    diagnosis: IncidentDiagnosisSummaryResponse
    recommended_workshops: list[RecommendedWorkshopResponse] = Field(default_factory=list)
    has_recommendations: bool
    top_recommendation_workshop_id: int | None = None
    message: str


class ServicePrequotationResponse(BaseModel):
    service_id: int
    incident_id: int
    prequotation_code: str | None = None
    prequotation_min: Decimal | None = None
    prequotation_max: Decimal | None = None
    prequotation_currency: str | None = "BOB"
    catalog_service_name: str | None = None
    incluye_repuestos_basicos: bool | None = None
    message: str


class ClientActiveServiceSummaryResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    incident_state: str
    workshop_name: str | None = None
    operario_name: str | None = None
    detected_specialty: str | None = None
    ai_summary: str | None = None
    prequotation_code: str | None = None
    prequotation_min: Decimal | None = None
    prequotation_max: Decimal | None = None
    prequotation_currency: str | None = "BOB"
    created_at: datetime | None = None
    assigned_at: datetime | None = None


class HireWorkshopRequest(_NormalizedModel):
    workshop_id: int


class HireWorkshopResponse(BaseModel):
    incident_id: int
    request_id: int
    workshop_id: int
    workshop_name: str
    request_state: str
    message: str
