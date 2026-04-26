from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from decimal import Decimal

from fastapi import Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.models import (
    Administrador,
    Bitacora,
    CoberturaEspecialidad,
    Incidente,
    MetodoPago,
    Notificacion,
    Pago,
    Seguro,
    Servicio,
    SolicitudServicio,
    Taller,
    TipoCobertura,
    Usuario,
)
from app.packages.seguridad_usuarios.security import utc_now

from .payment_provider import (
    PaymentProviderError,
    initiate_payment,
    initiate_subscription_payment,
)
from .schemas import (
    CoveragePlanResponse,
    CoverageSpecialtyResponse,
    PaymentInitiationRequest,
    PaymentInitiationResponse,
    PaymentMethodResponse,
    PaymentStatusResponse,
    PaymentStatusSummary,
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


settings = get_settings()
PAYABLE_SERVICE_STATE = "FINALIZADO_PENDIENTE_PAGO"
PAID_SERVICE_STATE = "PAGADO"
SUBSCRIPTION_DEFAULT_DURATION_DAYS = 365


def _build_service_query():
    return select(Servicio).options(
        joinedload(Servicio.pago).joinedload(Pago.metodo),
        joinedload(Servicio.solicitud).joinedload(SolicitudServicio.incidente),
        joinedload(Servicio.solicitud).joinedload(SolicitudServicio.taller),
    )


def _build_workshop_query():
    return select(Taller)


def _build_subscription_query():
    return select(Seguro).options(
        joinedload(Seguro.cobertura)
        .selectinload(TipoCobertura.especialidades)
        .joinedload(CoberturaEspecialidad.especialidad),
        joinedload(Seguro.taller),
    )


def _get_client_owned_service(
    db: Session,
    *,
    service_id: int,
    cliente_id: int,
) -> Servicio:
    service = db.scalar(
        _build_service_query()
        .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
        .join(Incidente, Incidente.id_incidente == SolicitudServicio.id_incidente)
        .where(
            Servicio.id_servicio == service_id,
            Incidente.id_cliente == cliente_id,
        )
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client service not found.",
        )
    return service


def _get_payment_by_reference(db: Session, *, provider_reference: str) -> Pago:
    payment = db.scalar(
        select(Pago)
        .options(
            joinedload(Pago.metodo),
            joinedload(Pago.servicio)
            .joinedload(Servicio.solicitud)
            .joinedload(SolicitudServicio.incidente),
            joinedload(Pago.servicio)
            .joinedload(Servicio.solicitud)
            .joinedload(SolicitudServicio.taller),
        )
        .where(Pago.referencia_externa == provider_reference)
    )
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment reference not found.",
        )
    return payment


def _get_workshop_for_subscription(db: Session, *, workshop_id: int) -> Taller:
    workshop = db.scalar(_build_workshop_query().where(Taller.id_taller == workshop_id))
    if workshop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found.",
        )
    if not workshop.activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workshop is not eligible for coverage subscriptions.",
        )
    return workshop


def _get_latest_subscription(
    db: Session,
    *,
    cliente_id: int,
    workshop_id: int,
) -> Seguro | None:
    return db.scalar(
        _build_subscription_query()
        .where(
            Seguro.id_cliente == cliente_id,
            Seguro.id_taller == workshop_id,
        )
        .order_by(Seguro.updated_at.desc(), Seguro.id_seguro.desc())
    )


def _get_subscription_by_id(db: Session, *, subscription_id: int) -> Seguro:
    seguro = db.scalar(
        _build_subscription_query().where(Seguro.id_seguro == subscription_id)
    )
    if seguro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )
    return seguro


def _get_coverage_plan(db: Session, *, coverage_id: int) -> TipoCobertura:
    coverage = db.scalar(
        select(TipoCobertura)
        .options(
            selectinload(TipoCobertura.especialidades).joinedload(CoberturaEspecialidad.especialidad)
        )
        .where(TipoCobertura.id_cobertura == coverage_id)
    )
    if coverage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coverage plan not found.",
        )
    return coverage


def _serialize_coverage_plan(plan: TipoCobertura) -> CoveragePlanResponse:
    return CoveragePlanResponse(
        id_cobertura=plan.id_cobertura,
        nombre=plan.nombre,
        descripcion_plan=plan.descripcion_plan,
        covered_specialties=[
            CoverageSpecialtyResponse(
                id_especialidad=item.especialidad.id_especialidad,
                nombre=item.especialidad.nombre,
            )
            for item in sorted(plan.especialidades, key=lambda row: row.id_especialidad)
        ],
    )


def _serialize_subscription_summary(seguro: Seguro) -> SubscriptionSummaryResponse:
    return SubscriptionSummaryResponse(
        id_seguro=seguro.id_seguro,
        workshop_id=seguro.id_taller,
        workshop_name=seguro.taller.nombre_comercial,
        id_cobertura=seguro.id_cobertura,
        coverage_name=seguro.cobertura.nombre,
        numero_poliza=seguro.numero_poliza,
        activo=seguro.activo,
        fecha_inicio=seguro.fecha_inicio,
        fecha_fin=seguro.fecha_fin,
        monto_maximo=Decimal(seguro.monto_maximo) if seguro.monto_maximo is not None else None,
    )


def _serialize_subscription_status(workshop_id: int, seguro: Seguro | None) -> SubscriptionStatusResponse:
    if seguro is None:
        return SubscriptionStatusResponse(workshop_id=workshop_id)
    return SubscriptionStatusResponse(
        workshop_id=workshop_id,
        id_seguro=seguro.id_seguro,
        activo=seguro.activo,
        id_cobertura=seguro.id_cobertura,
        numero_poliza=seguro.numero_poliza,
        fecha_inicio=seguro.fecha_inicio,
        fecha_fin=seguro.fecha_fin,
        monto_maximo=Decimal(seguro.monto_maximo) if seguro.monto_maximo is not None else None,
        renewal_allowed=True,
    )


def _get_payment_methods(db: Session) -> list[MetodoPago]:
    return list(db.scalars(select(MetodoPago).order_by(MetodoPago.id_metodo)))


def _serialize_payment_method(method: MetodoPago) -> PaymentMethodResponse:
    return PaymentMethodResponse(
        id_metodo_pago=method.id_metodo,
        nombre=method.nombre,
        activo=method.activo,
    )


def _serialize_payment_status(payment: Pago) -> PaymentStatusSummary:
    method_name = payment.metodo.nombre if payment.metodo is not None else ""
    return PaymentStatusSummary(
        payment_id=payment.id_pago,
        payment_status=payment.estado,
        amount=Decimal(payment.monto),
        method=method_name,
        provider_reference=payment.referencia_externa,
        qr_url=payment.qr_url,
        receipt=payment.comprobante or payment.servicio.comprobante,
        requested_at=payment.fecha_solicitud,
        confirmed_at=payment.fecha_confirmacion,
        last_update=payment.updated_at,
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


def _get_user_by_persona_id(db: Session, *, persona_id: int) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.id_persona == persona_id))


def _create_notification(
    *,
    db: Session,
    user: Usuario,
    service: Servicio,
    title: str,
    message: str,
    payload: dict[str, object],
) -> None:
    db.add(
        Notificacion(
            id_usuario=user.id_usuario,
            id_servicio=service.id_servicio,
            id_solicitud=service.id_solicitud,
            canal="WEB",
            titulo=title,
            mensaje=message,
            payload=payload,
            estado="PENDIENTE",
        )
    )


def _create_payment_bitacora(
    *,
    user: Usuario | None,
    service: Servicio,
    action: str,
    description: str,
    payment: Pago,
    payload: dict[str, object] | None,
) -> Bitacora:
    return Bitacora(
        accion=action,
        tipo_evento="PAGO",
        descripcion=description,
        entidad_principal="PAGO",
        id_entidad_principal=payment.id_pago,
        datos_nuevos=payload,
        hash_evento="",
        id_usuario=user.id_usuario if user is not None else None,
        id_incidente=service.solicitud.incidente.id_incidente,
        id_solicitud=service.id_solicitud,
        id_servicio=service.id_servicio,
        id_pago=payment.id_pago,
    )


def _create_subscription_bitacora(
    *,
    user: Usuario | None,
    seguro: Seguro,
    action: str,
    description: str,
    payload: dict[str, object] | None,
) -> Bitacora:
    entity_id = user.id_usuario if user is not None else seguro.id_cliente
    return Bitacora(
        accion=action,
        tipo_evento="SEGURO",
        descripcion=description,
        entidad_principal="USUARIO",
        id_entidad_principal=entity_id,
        datos_nuevos=payload,
        hash_evento="",
        id_usuario=user.id_usuario if user is not None else None,
    )


def _validate_webhook_token(webhook_token: str | None) -> None:
    expected = settings.payment_webhook_token
    if not expected:
        return
    if webhook_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid payment webhook token.",
        )


def _create_subscription_notification(
    *,
    db: Session,
    user: Usuario,
    seguro: Seguro,
    title: str,
    message: str,
    payload: dict[str, object],
) -> None:
    db.add(
        Notificacion(
            id_usuario=user.id_usuario,
            canal="WEB",
            titulo=title,
            mensaje=message,
            payload=payload,
            estado="PENDIENTE",
        )
    )


def _find_subscription_initiation_by_reference(
    db: Session,
    *,
    provider_reference: str,
) -> tuple[Seguro, Bitacora] | None:
    events = list(
        db.scalars(
            select(Bitacora)
            .where(
                Bitacora.accion.in_(
                    (
                        "SUSCRIPCION_COBERTURA_INICIADA",
                        "SUSCRIPCION_COBERTURA_CONFIRMADA",
                        "SUSCRIPCION_COBERTURA_RECHAZADA",
                    )
                )
            )
            .order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
        )
    )
    matched_init: Bitacora | None = None
    for event in events:
        payload = event.datos_nuevos if isinstance(event.datos_nuevos, dict) else {}
        if payload.get("provider_reference") != provider_reference:
            continue
        if event.accion == "SUSCRIPCION_COBERTURA_INICIADA":
            matched_init = event
            break
        seguro_id = payload.get("id_seguro")
        if seguro_id is not None:
            seguro = _get_subscription_by_id(db, subscription_id=int(seguro_id))
            return seguro, event
    if matched_init is None:
        return None
    payload = matched_init.datos_nuevos if isinstance(matched_init.datos_nuevos, dict) else {}
    seguro_id = payload.get("id_seguro")
    if seguro_id is None:
        return None
    seguro = _get_subscription_by_id(db, subscription_id=int(seguro_id))
    return seguro, matched_init


def _get_subscription_pending_initiation(
    db: Session,
    *,
    seguro_id: int,
) -> Bitacora | None:
    events = list(
        db.scalars(
            select(Bitacora)
            .where(
                Bitacora.accion.in_(
                    (
                        "SUSCRIPCION_COBERTURA_INICIADA",
                        "SUSCRIPCION_COBERTURA_CONFIRMADA",
                        "SUSCRIPCION_COBERTURA_RECHAZADA",
                    )
                )
            )
            .order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
        )
    )
    for event in events:
        payload = event.datos_nuevos if isinstance(event.datos_nuevos, dict) else {}
        if payload.get("id_seguro") != seguro_id:
            continue
        if event.accion == "SUSCRIPCION_COBERTURA_INICIADA":
            return event
        return None
    return None


def _generate_policy_number(seguro: Seguro) -> str:
    return f"POL-{seguro.id_seguro}-{utc_now().strftime('%Y%m%d%H%M%S')}"


def _get_payable_amount(service: Servicio) -> Decimal:
    amount = service.costo_total
    if amount is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service total amount is not available for payment.",
        )
    amount_decimal = Decimal(amount).quantize(Decimal("0.01"))
    if amount_decimal < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service total amount is invalid for payment.",
        )
    return amount_decimal


def get_payment_summary(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> PaymentSummaryResponse:
    service = _get_client_owned_service(
        db,
        service_id=service_id,
        cliente_id=current_user.id_persona,
    )
    methods = _get_payment_methods(db)
    return PaymentSummaryResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=service.solicitud.incidente.id_incidente,
        total_amount_due=_get_payable_amount(service),
        spare_parts_cost=Decimal(service.costo_repuestos),
        labor_cost=Decimal(service.costo_mano_obra) if service.costo_mano_obra is not None else None,
        payment_methods=[_serialize_payment_method(item) for item in methods],
        payable_now=service.estado == PAYABLE_SERVICE_STATE,
        existing_payment=(
            _serialize_payment_status(service.pago) if service.pago is not None else None
        ),
    )


def get_payment_status(
    *,
    service_id: int,
    current_user: Usuario,
    db: Session,
) -> PaymentStatusResponse:
    service = _get_client_owned_service(
        db,
        service_id=service_id,
        cliente_id=current_user.id_persona,
    )
    return PaymentStatusResponse(
        service_id=service.id_servicio,
        service_state=service.estado,
        incident_id=service.solicitud.incidente.id_incidente,
        payment=_serialize_payment_status(service.pago) if service.pago is not None else None,
        payable_now=service.estado == PAYABLE_SERVICE_STATE,
    )


def list_workshop_coverage_plans(
    *,
    workshop_id: int,
    current_user: Usuario,
    db: Session,
) -> list[CoveragePlanResponse]:
    _get_workshop_for_subscription(db, workshop_id=workshop_id)
    plans = list(
        db.scalars(
            select(TipoCobertura)
            .options(
                selectinload(TipoCobertura.especialidades).joinedload(CoberturaEspecialidad.especialidad)
            )
            .order_by(TipoCobertura.id_cobertura)
        )
    )
    return [_serialize_coverage_plan(item) for item in plans]


def get_workshop_subscription_status(
    *,
    workshop_id: int,
    current_user: Usuario,
    db: Session,
) -> SubscriptionStatusResponse:
    _get_workshop_for_subscription(db, workshop_id=workshop_id)
    seguro = _get_latest_subscription(
        db,
        cliente_id=current_user.id_persona,
        workshop_id=workshop_id,
    )
    return _serialize_subscription_status(workshop_id, seguro)


def initiate_workshop_subscription(
    *,
    workshop_id: int,
    payload: SubscriptionInitiationRequest,
    current_user: Usuario,
    db: Session,
) -> SubscriptionInitiationResponse:
    workshop = _get_workshop_for_subscription(db, workshop_id=workshop_id)
    coverage = _get_coverage_plan(db, coverage_id=payload.id_cobertura)
    seguro = _get_latest_subscription(
        db,
        cliente_id=current_user.id_persona,
        workshop_id=workshop_id,
    )

    if seguro is None:
        seguro = Seguro(
            id_cliente=current_user.id_persona,
            id_taller=workshop_id,
            id_cobertura=coverage.id_cobertura,
            fecha_inicio=utc_now(),
            fecha_fin=None,
            activo=False,
        )
        db.add(seguro)
        db.flush()
    elif not seguro.activo:
        seguro.id_cobertura = coverage.id_cobertura
        seguro.fecha_inicio = utc_now()
        seguro.fecha_fin = None
        seguro.activo = False
        seguro.numero_poliza = None

    pending_event = _get_subscription_pending_initiation(db, seguro_id=seguro.id_seguro)
    if pending_event is not None:
        pending_payload = pending_event.datos_nuevos if isinstance(pending_event.datos_nuevos, dict) else {}
        expires_at = None
        expires_raw = pending_payload.get("expires_at")
        if isinstance(expires_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None
        return SubscriptionInitiationResponse(
            subscription_id=seguro.id_seguro,
            workshop_id=workshop.id_taller,
            workshop_name=workshop.nombre_comercial,
            id_cobertura=coverage.id_cobertura,
            coverage_name=coverage.nombre,
            activo=seguro.activo,
            qr_payload=pending_payload.get("qr_payload"),
            qr_url=pending_payload.get("qr_url"),
            payment_url=pending_payload.get("payment_url"),
            provider_reference=str(pending_payload.get("provider_reference", "")),
            expires_at=expires_at,
            message="Existing pending subscription initiation reused.",
        )

    try:
        provider_data = initiate_subscription_payment(
            subscription_id=seguro.id_seguro,
            workshop_id=workshop.id_taller,
            coverage_name=coverage.nombre,
            method_name="QR",
        )
    except PaymentProviderError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Subscription payment provider is not available.",
        ) from exc

    event_payload = {
        "id_seguro": seguro.id_seguro,
        "id_cliente": seguro.id_cliente,
        "id_taller": workshop.id_taller,
        "id_cobertura": coverage.id_cobertura,
        "activo": seguro.activo,
        "provider_reference": provider_data.provider_reference,
        "expires_at": provider_data.expires_at.isoformat(),
        "qr_payload": provider_data.qr_payload,
        "qr_url": provider_data.qr_url,
        "payment_url": provider_data.payment_url,
    }
    db.add(
        _create_subscription_bitacora(
            user=current_user,
            seguro=seguro,
            action="SUSCRIPCION_COBERTURA_INICIADA",
            description="El cliente inicio la suscripcion o renovacion de cobertura del taller.",
            payload=event_payload,
        )
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription initiation could not be persisted.",
        ) from exc

    return SubscriptionInitiationResponse(
        subscription_id=seguro.id_seguro,
        workshop_id=workshop.id_taller,
        workshop_name=workshop.nombre_comercial,
        id_cobertura=coverage.id_cobertura,
        coverage_name=coverage.nombre,
        activo=seguro.activo,
        qr_payload=provider_data.qr_payload,
        qr_url=provider_data.qr_url,
        payment_url=provider_data.payment_url,
        provider_reference=provider_data.provider_reference,
        expires_at=provider_data.expires_at,
        message="Subscription payment initiated successfully.",
    )


def process_subscription_webhook(
    *,
    payload: SubscriptionWebhookRequest,
    db: Session,
    webhook_token: str | None,
) -> SubscriptionWebhookResponse:
    _validate_webhook_token(webhook_token)
    resolved = _find_subscription_initiation_by_reference(
        db,
        provider_reference=payload.provider_reference,
    )
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription reference not found.",
        )
    seguro, event = resolved
    event_payload = event.datos_nuevos if isinstance(event.datos_nuevos, dict) else {}

    if event.accion in {"SUSCRIPCION_COBERTURA_CONFIRMADA", "SUSCRIPCION_COBERTURA_RECHAZADA"}:
        return SubscriptionWebhookResponse(
            subscription_id=seguro.id_seguro,
            activo=seguro.activo,
            provider_reference=payload.provider_reference,
            already_processed=True,
            numero_poliza=seguro.numero_poliza,
            message="Subscription webhook had already been processed.",
        )

    coverage_id = int(event_payload.get("id_cobertura", seguro.id_cobertura))
    coverage = _get_coverage_plan(db, coverage_id=coverage_id)
    client_user = _get_user_by_persona_id(db, persona_id=seguro.id_cliente)

    if payload.status == "CONFIRMADO":
        now = utc_now()
        base_start = now
        if seguro.activo and seguro.fecha_fin is not None and seguro.fecha_fin > now:
            base_start = seguro.fecha_fin
        elif seguro.activo and seguro.fecha_inicio is not None and seguro.fecha_inicio > now:
            base_start = seguro.fecha_inicio
        seguro.id_cobertura = coverage.id_cobertura
        seguro.fecha_inicio = base_start
        seguro.fecha_fin = base_start + timedelta(days=SUBSCRIPTION_DEFAULT_DURATION_DAYS)
        seguro.activo = True
        seguro.numero_poliza = _generate_policy_number(seguro)

        db.add(
            _create_subscription_bitacora(
                user=client_user,
                seguro=seguro,
                action="SUSCRIPCION_COBERTURA_CONFIRMADA",
                description="La suscripcion de cobertura fue confirmada y activada.",
                payload={
                    "id_seguro": seguro.id_seguro,
                    "id_cliente": seguro.id_cliente,
                    "id_taller": seguro.id_taller,
                    "id_cobertura": seguro.id_cobertura,
                    "activo": seguro.activo,
                    "provider_reference": payload.provider_reference,
                    "numero_poliza": seguro.numero_poliza,
                    "fecha_inicio": seguro.fecha_inicio.isoformat(),
                    "fecha_fin": seguro.fecha_fin.isoformat() if seguro.fecha_fin is not None else None,
                },
            )
        )
        if client_user is not None:
            _create_subscription_notification(
                db=db,
                user=client_user,
                seguro=seguro,
                title="Cobertura activada",
                message="Tu suscripcion de cobertura del taller fue activada correctamente.",
                payload={
                    "id_seguro": seguro.id_seguro,
                    "id_taller": seguro.id_taller,
                    "id_cobertura": seguro.id_cobertura,
                    "numero_poliza": seguro.numero_poliza,
                },
            )
    else:
        if not seguro.activo:
            seguro.id_cobertura = coverage.id_cobertura
        db.add(
            _create_subscription_bitacora(
                user=client_user,
                seguro=seguro,
                action="SUSCRIPCION_COBERTURA_RECHAZADA",
                description="La suscripcion de cobertura no fue confirmada por la pasarela sandbox.",
                payload={
                    "id_seguro": seguro.id_seguro,
                    "id_cliente": seguro.id_cliente,
                    "id_taller": seguro.id_taller,
                    "id_cobertura": coverage.id_cobertura,
                    "activo": seguro.activo,
                    "provider_reference": payload.provider_reference,
                    "status": payload.status,
                },
            )
        )
        if client_user is not None:
            _create_subscription_notification(
                db=db,
                user=client_user,
                seguro=seguro,
                title="Cobertura no activada",
                message="La suscripcion de cobertura no pudo confirmarse. Puedes volver a intentarlo.",
                payload={
                    "id_seguro": seguro.id_seguro,
                    "id_taller": seguro.id_taller,
                    "id_cobertura": coverage.id_cobertura,
                    "status": payload.status,
                },
            )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription webhook could not be persisted.",
        ) from exc

    return SubscriptionWebhookResponse(
        subscription_id=seguro.id_seguro,
        activo=seguro.activo,
        provider_reference=payload.provider_reference,
        already_processed=False,
        numero_poliza=seguro.numero_poliza,
        message="Subscription webhook processed successfully.",
    )


def list_my_subscriptions(
    *,
    current_user: Usuario,
    db: Session,
) -> list[SubscriptionSummaryResponse]:
    seguros = list(
        db.scalars(
            _build_subscription_query()
            .where(Seguro.id_cliente == current_user.id_persona)
            .order_by(Seguro.updated_at.desc(), Seguro.id_seguro.desc())
        )
    )
    return [_serialize_subscription_summary(item) for item in seguros]


def initiate_service_payment(
    *,
    service_id: int,
    payload: PaymentInitiationRequest,
    current_user: Usuario,
    db: Session,
) -> PaymentInitiationResponse:
    service = _get_client_owned_service(
        db,
        service_id=service_id,
        cliente_id=current_user.id_persona,
    )
    if service.estado != PAYABLE_SERVICE_STATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is not ready for payment.",
        )
    amount = _get_payable_amount(service)

    method = db.scalar(select(MetodoPago).where(MetodoPago.id_metodo == payload.id_metodo_pago))
    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found.",
        )
    if not method.activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment method is inactive.",
        )

    payment = service.pago
    if payment is not None:
        if payment.estado == "CONFIRMADO" or service.estado == PAID_SERVICE_STATE:
            return PaymentInitiationResponse(
                payment_id=payment.id_pago,
                payment_status=payment.estado,
                amount=Decimal(payment.monto),
                method=payment.metodo.nombre,
                qr_payload=(payment.payload_pasarela or {}).get("qr_payload") if payment.payload_pasarela else None,
                qr_url=payment.qr_url,
                payment_url=(payment.payload_pasarela or {}).get("payment_url") if payment.payload_pasarela else None,
                expires_at=None,
                provider_reference=payment.referencia_externa or "",
                message="Payment was already confirmed for this service.",
            )
        if payment.estado == "PENDIENTE" and payment.id_metodo == method.id_metodo:
            payload_pasarela = payment.payload_pasarela or {}
            expires_raw = payload_pasarela.get("expires_at")
            expires_at = None
            if isinstance(expires_raw, str):
                try:
                    expires_at = datetime.fromisoformat(expires_raw)
                except ValueError:
                    expires_at = None
            return PaymentInitiationResponse(
                payment_id=payment.id_pago,
                payment_status=payment.estado,
                amount=Decimal(payment.monto),
                method=method.nombre,
                qr_payload=payload_pasarela.get("qr_payload") if isinstance(payload_pasarela, dict) else None,
                qr_url=payment.qr_url,
                payment_url=payload_pasarela.get("payment_url") if isinstance(payload_pasarela, dict) else None,
                expires_at=expires_at,
                provider_reference=payment.referencia_externa or "",
                message="Existing pending payment reused for this service.",
            )
        if payment.estado == "PENDIENTE" and payment.id_metodo != method.id_metodo:
            payment.estado = "ANULADO"

    if payment is None:
        payment = Pago(
            id_servicio=service.id_servicio,
            id_metodo=method.id_metodo,
            monto=amount,
            estado="PENDIENTE",
        )
        payment.metodo = method
        db.add(payment)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A payment already exists for this service.",
            ) from exc
    else:
        payment.id_metodo = method.id_metodo
        payment.metodo = method
        payment.monto = amount
        payment.estado = "PENDIENTE"
        payment.fecha_confirmacion = None
        payment.comprobante = None
        payment.servicio.comprobante = None
        payment.payload_pasarela = None
        payment.qr_url = None
        payment.token_pago = None
        payment.referencia_externa = None

    try:
        provider_data = initiate_payment(
            payment_id=payment.id_pago,
            amount=amount,
            method_name=method.nombre,
            service_id=service.id_servicio,
        )
    except PaymentProviderError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider is not available.",
        ) from exc

    payment.referencia_externa = provider_data.provider_reference
    payment.token_pago = provider_data.token_pago
    payment.qr_url = provider_data.qr_url
    payment.payload_pasarela = provider_data.payload_pasarela
    payment.fecha_confirmacion = None

    db.add(
        _create_payment_bitacora(
            user=current_user,
            service=service,
            action="PAGO_INICIADO",
            description="El cliente inicio el pago del servicio.",
            payment=payment,
            payload={
                "previous_state": service.estado,
                "payment_state": payment.estado,
                "provider_reference": payment.referencia_externa,
                "id_metodo_pago": method.id_metodo,
                "monto": f"{amount:.2f}",
            },
        )
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment initiation could not be persisted.",
        ) from exc

    return PaymentInitiationResponse(
        payment_id=payment.id_pago,
        payment_status=payment.estado,
        amount=Decimal(payment.monto),
        method=method.nombre,
        qr_payload=provider_data.qr_payload,
        qr_url=provider_data.qr_url,
        payment_url=provider_data.payment_url,
        expires_at=provider_data.expires_at,
        provider_reference=provider_data.provider_reference,
        message="Payment initiated successfully.",
    )


def process_payment_webhook(
    *,
    payload: PaymentWebhookRequest,
    db: Session,
    webhook_token: str | None,
) -> PaymentWebhookResponse:
    _validate_webhook_token(webhook_token)
    payment = _get_payment_by_reference(db, provider_reference=payload.provider_reference)
    service = payment.servicio

    if payment.estado == payload.status:
        return PaymentWebhookResponse(
            payment_id=payment.id_pago,
            payment_status=payment.estado,
            service_id=service.id_servicio,
            service_state=service.estado,
            provider_reference=payload.provider_reference,
            already_processed=True,
            message="Payment webhook had already been processed.",
        )

    if payment.estado == "CONFIRMADO":
        return PaymentWebhookResponse(
            payment_id=payment.id_pago,
            payment_status=payment.estado,
            service_id=service.id_servicio,
            service_state=service.estado,
            provider_reference=payload.provider_reference,
            already_processed=True,
            message="Payment was already confirmed.",
        )

    payment.estado = payload.status
    payment.payload_pasarela = {
        **(payment.payload_pasarela or {}),
        **({"webhook_payload": payload.payload} if payload.payload is not None else {}),
        "last_status": payload.status,
        "last_webhook_at": utc_now().isoformat(),
    }

    if payload.status == "CONFIRMADO":
        confirmed_at = utc_now()
        payment.fecha_confirmacion = confirmed_at
        receipt = payload.receipt or f"COMP-{payment.id_pago}-{confirmed_at.strftime('%Y%m%d%H%M%S')}"
        payment.comprobante = receipt
        service.comprobante = receipt

        if service.estado != PAID_SERVICE_STATE:
            service.estado = PAID_SERVICE_STATE

        db.add(
            _create_payment_bitacora(
                user=None,
                service=service,
                action="PAGO_CONFIRMADO",
                description="La pasarela confirmo el pago del servicio.",
                payment=payment,
                payload={
                    "previous_state": PAYABLE_SERVICE_STATE,
                    "new_state": service.estado,
                    "payment_state": payment.estado,
                    "provider_reference": payload.provider_reference,
                    "comprobante": receipt,
                },
            )
        )
        if service.estado == PAID_SERVICE_STATE:
            db.add(
                _create_payment_bitacora(
                    user=None,
                    service=service,
                    action="SERVICIO_PAGADO",
                    description="El servicio paso al estado PAGADO tras la confirmacion del pago.",
                    payment=payment,
                    payload={
                        "new_state": service.estado,
                        "payment_state": payment.estado,
                        "provider_reference": payload.provider_reference,
                    },
                )
            )

        client_user = db.scalar(select(Usuario).where(Usuario.id_persona == service.solicitud.incidente.id_cliente))
        if client_user is not None:
            _create_notification(
                db=db,
                user=client_user,
                service=service,
                title="Pago confirmado",
                message="Tu pago fue confirmado y el servicio quedo pagado.",
                payload={
                    "service_id": service.id_servicio,
                    "payment_id": payment.id_pago,
                    "payment_state": payment.estado,
                    "service_state": service.estado,
                    "comprobante": receipt,
                },
            )
        for admin_user in _get_workshop_admin_users(db, workshop_id=service.solicitud.id_taller):
            _create_notification(
                db=db,
                user=admin_user,
                service=service,
                title="Pago confirmado del servicio",
                message=f"El servicio {service.id_servicio} ya fue pagado por el cliente.",
                payload={
                    "service_id": service.id_servicio,
                    "payment_id": payment.id_pago,
                    "payment_state": payment.estado,
                    "service_state": service.estado,
                },
            )
    else:
        db.add(
            _create_payment_bitacora(
                user=None,
                service=service,
                action="PAGO_RECHAZADO" if payload.status == "RECHAZADO" else "PAGO_ANULADO",
                description="La pasarela reporto que el pago no fue confirmado.",
                payment=payment,
                payload={
                    "payment_state": payment.estado,
                    "provider_reference": payload.provider_reference,
                },
            )
        )
        client_user = db.scalar(select(Usuario).where(Usuario.id_persona == service.solicitud.incidente.id_cliente))
        if client_user is not None:
            _create_notification(
                db=db,
                user=client_user,
                service=service,
                title="Pago no confirmado",
                message="El intento de pago no fue confirmado. Puedes volver a intentarlo.",
                payload={
                    "service_id": service.id_servicio,
                    "payment_id": payment.id_pago,
                    "payment_state": payment.estado,
                    "service_state": service.estado,
                },
            )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment webhook could not be persisted.",
        ) from exc

    return PaymentWebhookResponse(
        payment_id=payment.id_pago,
        payment_status=payment.estado,
        service_id=service.id_servicio,
        service_state=service.estado,
        provider_reference=payload.provider_reference,
        already_processed=False,
        message="Payment webhook processed successfully.",
    )
