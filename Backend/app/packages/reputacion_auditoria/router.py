from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.operaciones_taller.dependencies import (
    WorkshopAdminContext,
    require_workshop_admin_context,
)
from app.packages.seguridad_usuarios.dependencies import get_current_profile_user

from .schemas import (
    AuditLogDetailResponse,
    AuditLogFilterOptionsResponse,
    AuditLogPageResponse,
    AuditTimelineItemResponse,
    RatingReminderResponse,
    ServiceRatingRequest,
    ServiceRatingResponse,
    ServiceRatingStatusResponse,
)
from .service import (
    create_rating_reminder,
    export_workshop_audit_logs_csv,
    get_rating_status,
    get_workshop_audit_filter_options,
    get_workshop_audit_log_detail,
    get_workshop_service_timeline,
    list_workshop_audit_logs,
    submit_service_rating,
)


router = APIRouter(prefix="/reputation", tags=["reputation"])


@router.get(
    "/audit-logs/filter-options",
    response_model=AuditLogFilterOptionsResponse,
)
def reputation_audit_log_filter_options(
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> AuditLogFilterOptionsResponse:
    return get_workshop_audit_filter_options(
        admin_context=admin_context,
        db=db,
    )


@router.get("/audit-logs/export.csv")
def reputation_audit_log_export_csv(
    service_id: int | None = None,
    incident_id: int | None = None,
    request_id: int | None = None,
    payment_id: int | None = None,
    actor_user_id: int | None = None,
    event_type: str | None = None,
    action: str | None = None,
    main_entity: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> Response:
    return export_workshop_audit_logs_csv(
        admin_context=admin_context,
        db=db,
        service_id=service_id,
        incident_id=incident_id,
        request_id=request_id,
        payment_id=payment_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        action=action,
        main_entity=main_entity,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.get(
    "/audit-logs",
    response_model=AuditLogPageResponse,
)
def reputation_audit_logs(
    service_id: int | None = None,
    incident_id: int | None = None,
    request_id: int | None = None,
    payment_id: int | None = None,
    actor_user_id: int | None = None,
    event_type: str | None = None,
    action: str | None = None,
    main_entity: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> AuditLogPageResponse:
    return list_workshop_audit_logs(
        admin_context=admin_context,
        db=db,
        service_id=service_id,
        incident_id=incident_id,
        request_id=request_id,
        payment_id=payment_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        action=action,
        main_entity=main_entity,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/services/{service_id}/timeline",
    response_model=list[AuditTimelineItemResponse],
)
def reputation_service_timeline(
    service_id: int,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> list[AuditTimelineItemResponse]:
    return get_workshop_service_timeline(
        service_id=service_id,
        admin_context=admin_context,
        db=db,
    )


@router.get(
    "/audit-logs/{audit_id}",
    response_model=AuditLogDetailResponse,
)
def reputation_audit_log_detail(
    audit_id: int,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> AuditLogDetailResponse:
    return get_workshop_audit_log_detail(
        audit_id=audit_id,
        admin_context=admin_context,
        db=db,
    )


@router.get(
    "/services/{service_id}/rating-status",
    response_model=ServiceRatingStatusResponse,
)
def reputation_service_rating_status(
    service_id: int,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> ServiceRatingStatusResponse:
    return get_rating_status(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/services/{service_id}/rating",
    response_model=ServiceRatingResponse,
)
def reputation_service_rating_submit(
    service_id: int,
    payload: ServiceRatingRequest,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> ServiceRatingResponse:
    return submit_service_rating(
        service_id=service_id,
        payload=payload,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/services/{service_id}/rating-reminder",
    response_model=RatingReminderResponse,
)
def reputation_service_rating_reminder(
    service_id: int,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> RatingReminderResponse:
    return create_rating_reminder(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )
