from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.seguridad_usuarios.dependencies import require_cliente_user

from .schemas import (
    CoveragePlanResponse,
    PaymentInitiationRequest,
    PaymentInitiationResponse,
    PaymentStatusResponse,
    PaymentSummaryResponse,
    PaymentWebhookRequest,
    PaymentWebhookResponse,
    SubscriptionInitiationRequest,
    SubscriptionInitiationResponse,
    SubscriptionStatusResponse,
    SubscriptionSummaryResponse,
    SubscriptionWebhookRequest,
    SubscriptionWebhookResponse,
)
from .service import (
    get_payment_status,
    get_payment_summary,
    get_workshop_subscription_status,
    initiate_service_payment,
    initiate_workshop_subscription,
    list_my_subscriptions,
    list_workshop_coverage_plans,
    process_payment_webhook,
    process_subscription_webhook,
)


router = APIRouter(tags=["finance-payments"])
finance_router = APIRouter(prefix="/finance", tags=["finance-payments"])


@finance_router.get(
    "/services/{service_id}/payment-summary",
    response_model=PaymentSummaryResponse,
)
def finance_service_payment_summary(
    service_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> PaymentSummaryResponse:
    return get_payment_summary(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@finance_router.post(
    "/services/{service_id}/payments/initiate",
    response_model=PaymentInitiationResponse,
)
def finance_service_payment_initiate(
    service_id: int,
    payload: PaymentInitiationRequest,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> PaymentInitiationResponse:
    return initiate_service_payment(
        service_id=service_id,
        payload=payload,
        current_user=current_user,
        db=db,
    )


@finance_router.get(
    "/services/{service_id}/payments/status",
    response_model=PaymentStatusResponse,
)
def finance_service_payment_status(
    service_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> PaymentStatusResponse:
    return get_payment_status(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@finance_router.get(
    "/workshops/{workshop_id}/coverage-plans",
    response_model=list[CoveragePlanResponse],
)
def finance_workshop_coverage_plans(
    workshop_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> list[CoveragePlanResponse]:
    return list_workshop_coverage_plans(
        workshop_id=workshop_id,
        current_user=current_user,
        db=db,
    )


@finance_router.get(
    "/workshops/{workshop_id}/subscription-status",
    response_model=SubscriptionStatusResponse,
)
def finance_workshop_subscription_status(
    workshop_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> SubscriptionStatusResponse:
    return get_workshop_subscription_status(
        workshop_id=workshop_id,
        current_user=current_user,
        db=db,
    )


@finance_router.post(
    "/workshops/{workshop_id}/subscriptions/initiate",
    response_model=SubscriptionInitiationResponse,
)
def finance_workshop_subscription_initiate(
    workshop_id: int,
    payload: SubscriptionInitiationRequest,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> SubscriptionInitiationResponse:
    return initiate_workshop_subscription(
        workshop_id=workshop_id,
        payload=payload,
        current_user=current_user,
        db=db,
    )


@finance_router.post(
    "/payments/webhook",
    response_model=PaymentWebhookResponse,
)
def finance_payment_webhook(
    payload: PaymentWebhookRequest,
    x_payment_webhook_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    return process_payment_webhook(
        payload=payload,
        db=db,
        webhook_token=x_payment_webhook_token,
    )


@finance_router.post(
    "/subscriptions/webhook",
    response_model=SubscriptionWebhookResponse,
)
def finance_subscription_webhook(
    payload: SubscriptionWebhookRequest,
    x_payment_webhook_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> SubscriptionWebhookResponse:
    return process_subscription_webhook(
        payload=payload,
        db=db,
        webhook_token=x_payment_webhook_token,
    )


@finance_router.get(
    "/subscriptions/me",
    response_model=list[SubscriptionSummaryResponse],
)
def finance_subscriptions_me(
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> list[SubscriptionSummaryResponse]:
    return list_my_subscriptions(
        current_user=current_user,
        db=db,
    )


router.include_router(finance_router)
