from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _NormalizedModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class PaymentMethodResponse(BaseModel):
    id_metodo_pago: int
    nombre: str
    activo: bool


class PaymentStatusSummary(BaseModel):
    payment_id: int
    payment_status: str
    amount: Decimal
    method: str
    provider_reference: str | None = None
    qr_url: str | None = None
    receipt: str | None = None
    requested_at: datetime
    confirmed_at: datetime | None = None
    last_update: datetime


class PaymentSummaryResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    total_amount_due: Decimal
    spare_parts_cost: Decimal
    labor_cost: Decimal | None = None
    payment_methods: list[PaymentMethodResponse]
    payable_now: bool
    existing_payment: PaymentStatusSummary | None = None


class PaymentInitiationRequest(_NormalizedModel):
    id_metodo_pago: int


class PaymentInitiationResponse(BaseModel):
    payment_id: int
    payment_status: str
    amount: Decimal
    method: str
    qr_payload: str | None = None
    qr_url: str | None = None
    payment_url: str | None = None
    expires_at: datetime | None = None
    provider_reference: str | None = None
    message: str


class PaymentStatusResponse(BaseModel):
    service_id: int
    service_state: str
    incident_id: int
    payment: PaymentStatusSummary | None = None
    payable_now: bool


class PaymentWebhookRequest(_NormalizedModel):
    provider_reference: str = Field(min_length=1, max_length=100)
    status: str
    receipt: str | None = None
    payload: dict[str, object] | None = None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CONFIRMADO", "RECHAZADO", "ANULADO"}:
            raise ValueError("status must be CONFIRMADO, RECHAZADO or ANULADO.")
        return normalized


class PaymentWebhookResponse(BaseModel):
    payment_id: int
    payment_status: str
    service_id: int
    service_state: str
    provider_reference: str
    already_processed: bool = False
    message: str


class CoverageSpecialtyResponse(BaseModel):
    id_especialidad: int
    nombre: str


class CoveragePlanResponse(BaseModel):
    id_cobertura: int
    nombre: str
    descripcion_plan: str | None = None
    covered_specialties: list[CoverageSpecialtyResponse]


class SubscriptionStatusResponse(BaseModel):
    workshop_id: int
    id_seguro: int | None = None
    activo: bool = False
    id_cobertura: int | None = None
    numero_poliza: str | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    monto_maximo: Decimal | None = None
    renewal_allowed: bool = True


class SubscriptionInitiationRequest(_NormalizedModel):
    id_cobertura: int


class SubscriptionInitiationResponse(BaseModel):
    subscription_id: int
    workshop_id: int
    workshop_name: str
    id_cobertura: int
    coverage_name: str
    activo: bool
    qr_payload: str | None = None
    qr_url: str | None = None
    payment_url: str | None = None
    provider_reference: str
    expires_at: datetime | None = None
    message: str


class SubscriptionWebhookRequest(_NormalizedModel):
    provider_reference: str = Field(min_length=1, max_length=100)
    status: str
    receipt: str | None = None
    payload: dict[str, object] | None = None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CONFIRMADO", "RECHAZADO", "ANULADO"}:
            raise ValueError("status must be CONFIRMADO, RECHAZADO or ANULADO.")
        return normalized


class SubscriptionWebhookResponse(BaseModel):
    subscription_id: int
    activo: bool
    provider_reference: str
    already_processed: bool = False
    numero_poliza: str | None = None
    message: str


class SubscriptionSummaryResponse(BaseModel):
    id_seguro: int
    workshop_id: int
    workshop_name: str
    id_cobertura: int
    coverage_name: str
    numero_poliza: str | None = None
    activo: bool
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    monto_maximo: Decimal | None = None
