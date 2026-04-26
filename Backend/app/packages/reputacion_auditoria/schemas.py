from __future__ import annotations

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
