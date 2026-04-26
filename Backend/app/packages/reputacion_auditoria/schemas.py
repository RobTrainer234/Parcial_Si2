from __future__ import annotations

from typing import Any
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _NormalizedModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class AllowedRatingTargetResponse(BaseModel):
    target_type: str
    target_id: int | None = None
    label: str


class ExistingRatingResponse(BaseModel):
    rating_id: int
    target_type: str
    target_id: int | None = None
    estrellas: int
    comentario: str | None = None
    fecha: datetime


class ServiceRatingStatusResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    actor_type: str
    allowed_targets: list[AllowedRatingTargetResponse]
    existing_ratings: list[ExistingRatingResponse]


class ServiceRatingRequest(_NormalizedModel):
    target_type: str
    target_id: int | None = None
    estrellas: int = Field(ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=2000)

    @field_validator("target_type")
    @classmethod
    def normalize_target_type(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"TALLER", "PERSONA"}:
            raise ValueError("target_type must be TALLER or PERSONA.")
        return normalized


class ServiceRatingResponse(BaseModel):
    service_id: int
    actor_type: str
    target_type: str
    target_id: int | None = None
    estrellas: int
    comentario: str | None = None
    rating_id: int
    updated_existing: bool
    recipient_reputation: Decimal | None = None
    message: str


class RatingReminderResponse(BaseModel):
    service_id: int
    actor_type: str
    incident_id: int
    pending_targets: list[AllowedRatingTargetResponse]
    reminder_created: bool
    message: str


AuditJsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class AuditActorSummary(BaseModel):
    user_id: int | None = None
    persona_id: int | None = None
    email: str | None = None
    tipo_usuario: str | None = None


class AuditLinkedEntitiesResponse(BaseModel):
    incident_id: int | None = None
    request_id: int | None = None
    service_id: int | None = None
    payment_id: int | None = None


class AuditLogItemResponse(BaseModel):
    audit_id: int
    timestamp: datetime
    action: str
    event_type: str
    description: str
    main_entity: str
    main_entity_id: int | None = None
    actor: AuditActorSummary | None = None
    linked: AuditLinkedEntitiesResponse
    hash_evento: str
    has_original_data: bool
    has_new_data: bool


class AuditLogDetailResponse(AuditLogItemResponse):
    datos_originales: AuditJsonValue = None
    datos_nuevos: AuditJsonValue = None
    ip_origen: str | None = None
    user_agent: str | None = None


class AuditLogPageResponse(BaseModel):
    items: list[AuditLogItemResponse]
    total: int
    limit: int
    offset: int
    has_next: bool


class AuditLogFilterOptionsResponse(BaseModel):
    event_types: list[str]
    actions: list[str]
    main_entities: list[str]


class AuditTimelineItemResponse(BaseModel):
    audit_id: int
    timestamp: datetime
    action: str
    event_type: str
    description: str
    service_state: str | None = None
    incident_state: str | None = None
