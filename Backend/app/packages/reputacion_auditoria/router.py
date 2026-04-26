from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.seguridad_usuarios.dependencies import get_current_profile_user

from .schemas import (
    RatingReminderResponse,
    ServiceRatingRequest,
    ServiceRatingResponse,
    ServiceRatingStatusResponse,
)
from .service import create_rating_reminder, get_rating_status, submit_service_rating


router = APIRouter(prefix="/reputation", tags=["reputation"])


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
