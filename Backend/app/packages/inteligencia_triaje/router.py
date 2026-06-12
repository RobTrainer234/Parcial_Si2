from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.seguridad_usuarios.dependencies import require_cliente_user, require_operario_user

from .schemas import (
    IncidentClassificationResponse,
    IncidentDetailResponse,
    IncidentReportCreateData,
    IncidentReportResponse,
    MatchmakingSelectionResponse,
    MatchmakingStatusResponse,
    OperarioAssignedServiceSummary,
    OperarioStructuredProfileResponse,
    SpecialtyResponse,
    StructuredProfileAcknowledgeResponse,
)
from .service import (
    acknowledge_operario_structured_profile,
    classify_incident,
    get_incident_detail,
    get_matchmaking_status,
    get_operario_structured_profile,
    list_operario_assigned_services,
    list_specialties,
    matchmake_incident,
    report_incident,
)


router = APIRouter(prefix="/triage", tags=["triage"])


@router.get("/specialties", response_model=list[SpecialtyResponse])
def triage_specialties(
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> list[SpecialtyResponse]:
    return list_specialties(db)

@router.post("/incidents/report", response_model=IncidentReportResponse, status_code=201)
def report_vehicle_incident(
    request: Request,
    id_vehiculo: int = Form(...),
    latitud: Decimal = Form(...),
    longitud: Decimal = Form(...),
    descripcion_cliente: str = Form(""),
    id_especialidad_reportada_cliente: int = Form(...),
    audio: UploadFile | None = File(default=None),
    images: list[UploadFile] | None = File(default=None),
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> IncidentReportResponse:
    payload = IncidentReportCreateData.model_validate(
        {
            "id_vehiculo": id_vehiculo,
            "latitud": latitud,
            "longitud": longitud,
            "descripcion_cliente": descripcion_cliente,
            "id_especialidad_reportada_cliente": id_especialidad_reportada_cliente,
        }
    )
    return report_incident(
        payload=payload,
        current_user=current_user,
        db=db,
        audio_file=audio,
        image_files=images or [],
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_vehicle_incident_detail(
    incident_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    return get_incident_detail(
        incident_id=incident_id,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/incidents/{incident_id}/classify",
    response_model=IncidentClassificationResponse,
)
def classify_vehicle_incident(
    request: Request,
    incident_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> IncidentClassificationResponse:
    return classify_incident(
        incident_id=incident_id,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/incidents/{incident_id}/matchmake",
    response_model=MatchmakingSelectionResponse,
)
def matchmake_vehicle_incident(
    request: Request,
    incident_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> MatchmakingSelectionResponse:
    return matchmake_incident(
        incident_id=incident_id,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/incidents/{incident_id}/matchmaking",
    response_model=MatchmakingStatusResponse,
)
def get_vehicle_incident_matchmaking_status(
    incident_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> MatchmakingStatusResponse:
    return get_matchmaking_status(
        incident_id=incident_id,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/operario/services/assigned",
    response_model=list[OperarioAssignedServiceSummary],
)
def list_assigned_operario_services(
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> list[OperarioAssignedServiceSummary]:
    return list_operario_assigned_services(
        current_user=current_user,
        db=db,
    )


@router.get(
    "/operario/services/{service_id}/structured-profile",
    response_model=OperarioStructuredProfileResponse,
)
def get_assigned_service_structured_profile(
    service_id: int,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> OperarioStructuredProfileResponse:
    return get_operario_structured_profile(
        service_id=service_id,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/operario/services/{service_id}/structured-profile/acknowledge",
    response_model=StructuredProfileAcknowledgeResponse,
)
def acknowledge_assigned_service_structured_profile(
    request: Request,
    service_id: int,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> StructuredProfileAcknowledgeResponse:
    return acknowledge_operario_structured_profile(
        service_id=service_id,
        current_user=current_user,
        db=db,
        ip_origen=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )
