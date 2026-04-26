from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.core.config import get_settings


settings = get_settings()


class PaymentProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class PaymentInitiationData:
    provider_reference: str
    token_pago: str
    qr_payload: str | None
    qr_url: str | None
    payment_url: str | None
    expires_at: datetime
    payload_pasarela: dict[str, object]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def initiate_payment(
    *,
    payment_id: int,
    amount: Decimal,
    method_name: str,
    service_id: int,
) -> PaymentInitiationData:
    if settings.payment_provider != "sandbox":
        raise PaymentProviderError("Configured payment provider is not supported.")

    now = _now_utc()
    provider_reference = f"pay_{payment_id}_{uuid4().hex[:12]}"
    token_pago = f"tok_{uuid4().hex}"
    expires_at = now + timedelta(minutes=settings.payment_request_expire_minutes)
    normalized_method = method_name.upper()

    qr_payload = None
    qr_url = None
    payment_url = None
    if normalized_method == "QR":
        qr_payload = (
            f"SANDBOX|SERVICE={service_id}|PAYMENT={payment_id}|AMOUNT={amount:.2f}|REF={provider_reference}"
        )
        qr_url = f"https://sandbox.local/qr/{provider_reference}"
    elif normalized_method in {"PAGO_MOVIL", "LINK", "TRANSFERENCIA"}:
        payment_url = f"https://sandbox.local/pay/{provider_reference}"

    return PaymentInitiationData(
        provider_reference=provider_reference,
        token_pago=token_pago,
        qr_payload=qr_payload,
        qr_url=qr_url,
        payment_url=payment_url,
        expires_at=expires_at,
        payload_pasarela={
            "provider": settings.payment_provider,
            "provider_reference": provider_reference,
            "token_pago": token_pago,
            "method": normalized_method,
            "amount": f"{amount:.2f}",
            "expires_at": expires_at.isoformat(),
            "qr_payload": qr_payload,
            "qr_url": qr_url,
            "payment_url": payment_url,
        },
    )


def initiate_subscription_payment(
    *,
    subscription_id: int,
    workshop_id: int,
    coverage_name: str,
    method_name: str = "QR",
) -> PaymentInitiationData:
    if settings.payment_provider != "sandbox":
        raise PaymentProviderError("Configured payment provider is not supported.")

    now = _now_utc()
    provider_reference = f"sub_{subscription_id}_{uuid4().hex[:12]}"
    token_pago = f"stok_{uuid4().hex}"
    expires_at = now + timedelta(minutes=settings.payment_request_expire_minutes)
    normalized_method = method_name.upper()

    qr_payload = None
    qr_url = None
    payment_url = None
    if normalized_method == "QR":
        qr_payload = (
            f"SANDBOX|SUBSCRIPTION={subscription_id}|WORKSHOP={workshop_id}|COVERAGE={coverage_name}|REF={provider_reference}"
        )
        qr_url = f"https://sandbox.local/subscription/qr/{provider_reference}"
    elif normalized_method in {"PAGO_MOVIL", "LINK", "TRANSFERENCIA"}:
        payment_url = f"https://sandbox.local/subscription/pay/{provider_reference}"

    return PaymentInitiationData(
        provider_reference=provider_reference,
        token_pago=token_pago,
        qr_payload=qr_payload,
        qr_url=qr_url,
        payment_url=payment_url,
        expires_at=expires_at,
        payload_pasarela={
            "provider": settings.payment_provider,
            "provider_reference": provider_reference,
            "token_pago": token_pago,
            "method": normalized_method,
            "subscription_id": subscription_id,
            "workshop_id": workshop_id,
            "coverage_name": coverage_name,
            "expires_at": expires_at.isoformat(),
            "qr_payload": qr_payload,
            "qr_url": qr_url,
            "payment_url": payment_url,
        },
    )
