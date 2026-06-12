from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.seguridad_usuarios.dependencies import require_operario_user

from .dependencies import (
    WorkshopAccessContext,
    WorkshopAdminContext,
    require_gerente_context,
    require_workshop_access,
    require_workshop_access_with_workshop_id,
    require_workshop_admin_context,
    require_workshop_read_context,
)
from .schemas import (
    AssignOperarioRequest,
    AssignOperarioResponse,
    FinalEvidenceResponse,
    OperarioCandidateSummary,
    RepairReportItemInput,
    RepairReportSaveResponse,
    RepairReportSnapshotResponse,
    UsedSparePartResponse,
    WaitingAssignmentServiceSummary,
    WorkshopActiveServiceTrackingSummary,
    WorkshopCatalogServiceCreateRequest,
    WorkshopCatalogServiceResponse,
    WorkshopCatalogServiceUpdateRequest,
    WorkshopDashboardOverviewResponse,
    VoiceDashboardReportResponse,
    WorkshopRequestDecisionRequest,
    WorkshopRequestDecisionResponse,
    WorkshopRequestDetailResponse,
    WorkshopRequestSummary,
    WorkshopMediaFileResponse,
    WorkshopMediaUploadRequest,
    WorkshopProfileResponse,
    WorkshopProfileUpdateRequest,
    WorkshopServiceHistoryDetailResponse,
    WorkshopServiceHistorySummary,
    WorkshopStaffAvailabilityUpdateRequest,
    WorkshopStaffCreateRequest,
    WorkshopStaffSummary,
    WorkshopSummaryResponse,
)
from .service import (
    activate_workshop_catalog_service,
    assign_operario_to_service,
    create_workshop_catalog_service,
    create_workshop_dashboard_voice_report,
    decide_workshop_request,
    deactivate_workshop_catalog_service,
    get_workshop_dashboard_overview,
    get_operario_candidates_for_service,
    get_repair_report_snapshot,
    get_workshop_profile,
    get_workshop_request_detail,
    get_workshop_service_history_detail,
    list_workshop_catalog_services,
    list_workshop_media_files,
    list_workshop_service_history,
    list_workshop_staff,
    list_waiting_assignment_services,
    list_pending_workshop_requests,
    deactivate_workshop_media_file,
    register_workshop_operario,
    save_repair_report,
    upload_workshop_media_file,
    update_workshop_catalog_service,
    update_workshop_profile,
    update_workshop_operario_availability,
)


router = APIRouter(prefix="/workshop", tags=["workshop-requests"])


@router.get("/dashboard/overview", response_model=WorkshopDashboardOverviewResponse)
def workshop_dashboard_overview(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> WorkshopDashboardOverviewResponse:
    return get_workshop_dashboard_overview(
        admin_context=admin_context,
        db=db,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/dashboard/ai-reports/audio", response_model=VoiceDashboardReportResponse)
def workshop_dashboard_voice_report(
    audio: UploadFile = File(...),
    date_from: datetime | None = Form(default=None),
    date_to: datetime | None = Form(default=None),
    scope: str | None = Form(default="TALLER"),
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> VoiceDashboardReportResponse:
    return create_workshop_dashboard_voice_report(
        admin_context=admin_context,
        db=db,
        audio_file=audio,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
    )


@router.get("/profile", response_model=WorkshopProfileResponse)
def workshop_profile(
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> WorkshopProfileResponse:
    return get_workshop_profile(admin_context=admin_context, db=db)


@router.put("/profile", response_model=WorkshopProfileResponse)
def workshop_profile_update(
    request: Request,
    payload: WorkshopProfileUpdateRequest,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopProfileResponse:
    return update_workshop_profile(
        payload=payload,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/catalog", response_model=list[WorkshopCatalogServiceResponse])
def workshop_catalog_list(
    include_inactive: bool = False,
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> list[WorkshopCatalogServiceResponse]:
    return list_workshop_catalog_services(
        include_inactive=include_inactive,
        admin_context=admin_context,
        db=db,
    )


@router.post("/catalog", response_model=WorkshopCatalogServiceResponse)
def workshop_catalog_create(
    request: Request,
    payload: WorkshopCatalogServiceCreateRequest,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopCatalogServiceResponse:
    return create_workshop_catalog_service(
        payload=payload,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.put("/catalog/{catalog_id}", response_model=WorkshopCatalogServiceResponse)
def workshop_catalog_update(
    request: Request,
    catalog_id: int,
    payload: WorkshopCatalogServiceUpdateRequest,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopCatalogServiceResponse:
    return update_workshop_catalog_service(
        catalog_id=catalog_id,
        payload=payload,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/catalog/{catalog_id}/deactivate", response_model=WorkshopCatalogServiceResponse)
def workshop_catalog_deactivate(
    request: Request,
    catalog_id: int,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopCatalogServiceResponse:
    return deactivate_workshop_catalog_service(
        catalog_id=catalog_id,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/catalog/{catalog_id}/activate", response_model=WorkshopCatalogServiceResponse)
def workshop_catalog_activate(
    request: Request,
    catalog_id: int,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopCatalogServiceResponse:
    return activate_workshop_catalog_service(
        catalog_id=catalog_id,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/profile/media", response_model=WorkshopMediaFileResponse)
def workshop_profile_media_upload(
    request: Request,
    tipo_archivo: str = Form(...),
    descripcion: str | None = Form(default=None),
    file: UploadFile = File(...),
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopMediaFileResponse:
    payload = WorkshopMediaUploadRequest(
        tipo_archivo=tipo_archivo,
        descripcion=descripcion,
    )
    return upload_workshop_media_file(
        payload=payload,
        file=file,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/profile/media", response_model=list[WorkshopMediaFileResponse])
def workshop_profile_media_list(
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> list[WorkshopMediaFileResponse]:
    return list_workshop_media_files(admin_context=admin_context, db=db)


@router.patch("/profile/media/{file_id}/deactivate", response_model=WorkshopMediaFileResponse)
def workshop_profile_media_deactivate(
    request: Request,
    file_id: int,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopMediaFileResponse:
    return deactivate_workshop_media_file(
        file_id=file_id,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/staff", response_model=list[WorkshopStaffSummary])
def workshop_staff_list(
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> list[WorkshopStaffSummary]:
    return list_workshop_staff(admin_context=admin_context, db=db)


@router.post("/staff", response_model=WorkshopStaffSummary)
def workshop_staff_create(
    request: Request,
    payload: WorkshopStaffCreateRequest,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopStaffSummary:
    return register_workshop_operario(
        payload=payload,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/staff/{operario_id}/availability", response_model=WorkshopStaffSummary)
def workshop_staff_availability_update(
    request: Request,
    operario_id: int,
    payload: WorkshopStaffAvailabilityUpdateRequest,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopStaffSummary:
    return update_workshop_operario_availability(
        operario_id=operario_id,
        payload=payload,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/requests/pending", response_model=list[WorkshopRequestSummary])
def workshop_pending_requests(
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> list[WorkshopRequestSummary]:
    return list_pending_workshop_requests(admin_context=admin_context, db=db)


@router.get("/requests/{request_id}", response_model=WorkshopRequestDetailResponse)
def workshop_request_detail(
    request_id: int,
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> WorkshopRequestDetailResponse:
    return get_workshop_request_detail(
        request_id=request_id,
        admin_context=admin_context,
        db=db,
    )


@router.post("/requests/{request_id}/decision", response_model=WorkshopRequestDecisionResponse)
def workshop_request_decision(
    request: Request,
    request_id: int,
    payload: WorkshopRequestDecisionRequest,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> WorkshopRequestDecisionResponse:
    return decide_workshop_request(
        request_id=request_id,
        payload=payload,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/services/history",
    response_model=list[WorkshopServiceHistorySummary],
)
def workshop_services_history(
    estado: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    operario_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> list[WorkshopServiceHistorySummary]:
    return list_workshop_service_history(
        admin_context=admin_context,
        db=db,
        estado=estado,
        desde=desde,
        hasta=hasta,
        operario_id=operario_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/services/{service_id}/history-detail",
    response_model=WorkshopServiceHistoryDetailResponse,
)
def workshop_service_history_detail(
    service_id: int,
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> WorkshopServiceHistoryDetailResponse:
    return get_workshop_service_history_detail(
        service_id=service_id,
        admin_context=admin_context,
        db=db,
    )


@router.get(
    "/services/waiting-assignment",
    response_model=list[WaitingAssignmentServiceSummary],
)
def workshop_services_waiting_assignment(
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> list[WaitingAssignmentServiceSummary]:
    return list_waiting_assignment_services(admin_context=admin_context, db=db)


@router.get(
    "/services/{service_id}/operario-candidates",
    response_model=list[OperarioCandidateSummary],
)
def workshop_service_operario_candidates(
    service_id: int,
    admin_context: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> list[OperarioCandidateSummary]:
    return get_operario_candidates_for_service(
        service_id=service_id,
        admin_context=admin_context,
        db=db,
    )


@router.post(
    "/services/{service_id}/assign-operario",
    response_model=AssignOperarioResponse,
)
def workshop_service_assign_operario(
    request: Request,
    service_id: int,
    payload: AssignOperarioRequest,
    admin_context: WorkshopAdminContext = Depends(require_workshop_admin_context),
    db: Session = Depends(get_db),
) -> AssignOperarioResponse:
    return assign_operario_to_service(
        service_id=service_id,
        payload=payload,
        admin_context=admin_context,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/services/{service_id}/repair-report",
    response_model=RepairReportSnapshotResponse,
)
def workshop_service_repair_report_snapshot(
    service_id: int,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> RepairReportSnapshotResponse:
    return get_repair_report_snapshot(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/services/{service_id}/repair-report",
    response_model=RepairReportSaveResponse,
)
def workshop_service_repair_report_save(
    request: Request,
    service_id: int,
    accion_realizada: str = Form(...),
    diagnostico_fisico: str | None = Form(default=None),
    observaciones: str | None = Form(default=None),
    recomendaciones: str | None = Form(default=None),
    used_items: str = Form(default="[]"),
    final_images: list[UploadFile] | None = File(default=None),
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> RepairReportSaveResponse:
    try:
        raw_items = json.loads(used_items)
        if not isinstance(raw_items, list):
            raise ValueError("used_items must be a JSON array.")
        parsed_items = [RepairReportItemInput.model_validate(item) for item in raw_items]
    except (json.JSONDecodeError, ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="used_items payload is invalid.",
        ) from exc

    return save_repair_report(
        service_id=service_id,
        accion_realizada=accion_realizada,
        diagnostico_fisico=diagnostico_fisico,
        observaciones=observaciones,
        recomendaciones=recomendaciones,
        used_items=parsed_items,
        final_images=final_images or [],
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/tracking/active",
    response_model=list[WorkshopActiveServiceTrackingSummary],
)
def workshop_tracking_active(
    access: WorkshopAdminContext | WorkshopAccessContext = Depends(require_workshop_read_context),
    db: Session = Depends(get_db),
) -> list[WorkshopActiveServiceTrackingSummary]:
    from app.packages.operaciones_taller.service import get_workshop_active_tracking
    workshop_ids: tuple[int, ...]
    if isinstance(access, WorkshopAdminContext):
        workshop_ids = (access.workshop_id,)
    else:
        workshop_ids = access.taller_ids
    return get_workshop_active_tracking(
        workshop_ids=workshop_ids,
        db=db,
    )


@router.get(
    "/gerente/workshops",
    response_model=list[WorkshopSummaryResponse],
)
def gerente_workshops_list(
    gerente_context: WorkshopAccessContext = Depends(require_gerente_context),
    db: Session = Depends(get_db),
) -> list[WorkshopSummaryResponse]:
    from app.models import Taller
    from sqlalchemy import select

    workshops = db.scalars(
        select(Taller).where(
            Taller.id_taller.in_(gerente_context.taller_ids),
            Taller.id_tenant == gerente_context.tenant_id,
        )
    ).all()
    return [
        WorkshopSummaryResponse(id_taller=w.id_taller, nombre_comercial=w.nombre_comercial)
        for w in workshops
    ]
