from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.seguridad_usuarios.dependencies import (
    get_current_profile_user,
    require_cliente_user,
    require_operario_user,
)

from .schemas import (
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    DeviceUnregisterRequest,
    DispatchPendingResponse,
    ClientActiveServiceSummaryResponse,
    FinalizationDecisionRequest,
    FinalizationDecisionResponse,
    FinalizationRequestResponse,
    FinalizationStatusResponse,
    HireWorkshopRequest,
    HireWorkshopResponse,
    IncidentRecommendationsResponse,
    NavigationStartRequest,
    NavigationStartResponse,
    NavigationStatusResponse,
    NotificationInboxItem,
    NotificationReadResponse,
    ServicePrequotationResponse,
    ServiceProgressHistoryItem,
    ServiceProgressSnapshotResponse,
    ServiceProgressUpdateRequest,
    ServiceProgressUpdateResponse,
    TrackingHistoryPointResponse,
    TrackingStatusResponse,
    UnreadCountResponse,
    ServiceLocationUpdateRequest,
    ServiceLocationUpdateResponse,
)
from .service import (
    dispatch_pending_notifications,
    get_my_notifications,
    get_my_unread_notification_count,
    hire_incident_workshop,
    get_incident_recommendations,
    get_client_service_prequotation,
    list_client_active_services,
    decide_service_finalization,
    mark_notification_as_read,
    register_notification_device,
    unregister_notification_device,
    get_client_tracking_history,
    get_client_tracking_status,
    get_finalization_status,
    get_navigation_status,
    get_service_progress_history,
    get_service_progress_snapshot,
    request_service_finalization,
    start_navigation,
    update_service_location,
    update_service_progress,
)

router = APIRouter(tags=["field-navigation"])
field_router = APIRouter(prefix="/field", tags=["field-navigation"])
client_router = APIRouter(prefix="/client", tags=["client-services"])
tracking_router = APIRouter(prefix="/tracking", tags=["client-tracking"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])
assistance_router = APIRouter(prefix="/assistance", tags=["client-assistance"])


@field_router.post(
    "/services/{service_id}/navigation/start",
    response_model=NavigationStartResponse,
)
def field_navigation_start(
    request: Request,
    service_id: int,
    payload: NavigationStartRequest,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> NavigationStartResponse:
    return start_navigation(
        service_id=service_id,
        payload=payload,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@field_router.post(
    "/services/{service_id}/location",
    response_model=ServiceLocationUpdateResponse,
)
def field_service_location_update(
    request: Request,
    service_id: int,
    payload: ServiceLocationUpdateRequest,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> ServiceLocationUpdateResponse:
    return update_service_location(
        service_id=service_id,
        payload=payload,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@field_router.get(
    "/services/{service_id}/navigation/status",
    response_model=NavigationStatusResponse,
)
def field_navigation_status(
    service_id: int,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> NavigationStatusResponse:
    return get_navigation_status(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@field_router.get(
    "/services/{service_id}/progress",
    response_model=ServiceProgressSnapshotResponse,
)
def field_service_progress_snapshot(
    service_id: int,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> ServiceProgressSnapshotResponse:
    return get_service_progress_snapshot(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@field_router.post(
    "/services/{service_id}/progress",
    response_model=ServiceProgressUpdateResponse,
)
def field_service_progress_update(
    request: Request,
    service_id: int,
    payload: ServiceProgressUpdateRequest,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> ServiceProgressUpdateResponse:
    return update_service_progress(
        service_id=service_id,
        payload=payload,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@field_router.get(
    "/services/{service_id}/progress/history",
    response_model=list[ServiceProgressHistoryItem],
)
def field_service_progress_history(
    service_id: int,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> list[ServiceProgressHistoryItem]:
    return get_service_progress_history(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@field_router.get(
    "/services/{service_id}/finalization-status",
    response_model=FinalizationStatusResponse,
)
def field_service_finalization_status(
    service_id: int,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> FinalizationStatusResponse:
    return get_finalization_status(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@field_router.post(
    "/services/{service_id}/finalization/request",
    response_model=FinalizationRequestResponse,
)
def field_service_finalization_request(
    request: Request,
    service_id: int,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> FinalizationRequestResponse:
    return request_service_finalization(
        service_id=service_id,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@client_router.post(
    "/services/{service_id}/finalization/decision",
    response_model=FinalizationDecisionResponse,
)
def client_service_finalization_decision(
    request: Request,
    service_id: int,
    payload: FinalizationDecisionRequest,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> FinalizationDecisionResponse:
    return decide_service_finalization(
        service_id=service_id,
        payload=payload,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@client_router.get(
    "/services/active",
    response_model=list[ClientActiveServiceSummaryResponse],
)
def client_active_services(
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> list[ClientActiveServiceSummaryResponse]:
    return list_client_active_services(
        current_user=current_user,
        db=db,
    )


@client_router.get(
    "/services/{service_id}/prequotation",
    response_model=ServicePrequotationResponse,
)
def client_service_prequotation(
    service_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> ServicePrequotationResponse:
    return get_client_service_prequotation(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@tracking_router.get(
    "/services/{service_id}/status",
    response_model=TrackingStatusResponse,
)
def tracking_service_status(
    service_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> TrackingStatusResponse:
    return get_client_tracking_status(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@tracking_router.get(
    "/services/{service_id}/history",
    response_model=list[TrackingHistoryPointResponse],
)
def tracking_service_history(
    service_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> list[TrackingHistoryPointResponse]:
    return get_client_tracking_history(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@assistance_router.get(
    "/incidents/{incident_id}/recommendations",
    response_model=IncidentRecommendationsResponse,
)
def assistance_incident_recommendations(
    incident_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> IncidentRecommendationsResponse:
    return get_incident_recommendations(
        incident_id=incident_id,
        current_user=current_user,
        db=db,
    )


@assistance_router.post(
    "/incidents/{incident_id}/hire",
    response_model=HireWorkshopResponse,
)
def assistance_hire_incident_workshop(
    request: Request,
    incident_id: int,
    payload: HireWorkshopRequest,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> HireWorkshopResponse:
    return hire_incident_workshop(
        incident_id=incident_id,
        payload=payload,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@notifications_router.post(
    "/devices/register",
    response_model=DeviceRegistrationResponse,
)
def notifications_device_register(
    request: Request,
    payload: DeviceRegistrationRequest,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> DeviceRegistrationResponse:
    return register_notification_device(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@notifications_router.post("/devices/unregister", response_model=DeviceRegistrationResponse)
def notifications_device_unregister(
    request: Request,
    payload: DeviceUnregisterRequest,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> DeviceRegistrationResponse:
    return unregister_notification_device(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@notifications_router.get("/me", response_model=list[NotificationInboxItem])
def notifications_me(
    only_unread: bool = False,
    limit: int = 50,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> list[NotificationInboxItem]:
    return get_my_notifications(
        current_user=current_user,
        db=db,
        only_unread=only_unread,
        limit=limit,
    )


@notifications_router.post(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
)
def notifications_mark_read(
    request: Request,
    notification_id: int,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> NotificationReadResponse:
    return mark_notification_as_read(
        notification_id=notification_id,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@notifications_router.get("/me/unread-count", response_model=UnreadCountResponse)
def notifications_unread_count(
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    return get_my_unread_notification_count(
        current_user=current_user,
        db=db,
    )


@notifications_router.post("/me/dispatch-pending", response_model=DispatchPendingResponse)
def notifications_dispatch_pending(
    request: Request,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> DispatchPendingResponse:
    return dispatch_pending_notifications(
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


router.include_router(field_router)
router.include_router(client_router)
router.include_router(tracking_router)
router.include_router(assistance_router)
router.include_router(notifications_router)
