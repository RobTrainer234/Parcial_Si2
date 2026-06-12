from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

from .dependencies import (
    get_current_profile_user,
    get_current_user,
    require_cliente_user,
    require_operario_user,
)
from .schemas import (
    AdminRegisterStartRequest,
    ClientRegisterStartRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    OperarioSpecialtyReplaceRequest,
    OperarioSpecialtyResponse,
    ProfileMeResponse,
    ProfileUpdateRequest,
    RegistrationStartResponse,
    RegistrationVerifyRequest,
    RegistrationVerifyResponse,
    ResetPasswordRequest,
    SimpleSuccessResponse,
    UserProfileResponse,
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateRequest,
)
from .service import (
    create_client_vehicle,
    delete_client_vehicle,
    forgot_password,
    get_me,
    get_profile_me,
    list_client_vehicles,
    list_operario_specialties,
    login_user,
    logout_user,
    replace_operario_specialties,
    reset_password,
    start_admin_registration,
    start_client_registration,
    update_client_vehicle,
    update_profile_me,
    verify_admin_registration,
    verify_client_registration,
)


auth_router = APIRouter(prefix="/auth", tags=["auth"])
profile_router = APIRouter(prefix="/profile", tags=["profile"])
router = APIRouter()


@auth_router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    return login_user(payload, db)


@auth_router.get("/me", response_model=UserProfileResponse)
def auth_me(current_user=Depends(get_current_user)) -> UserProfileResponse:
    return get_me(current_user)


@auth_router.post("/logout", response_model=LogoutResponse)
def logout(_: object = Depends(get_current_user)) -> LogoutResponse:
    return logout_user()


@auth_router.post("/register/client/start", response_model=RegistrationVerifyResponse)
def register_client_start(
    payload: ClientRegisterStartRequest,
    db: Session = Depends(get_db),
) -> RegistrationVerifyResponse:
    return start_client_registration(payload, db)


@auth_router.post("/register/client/verify", response_model=RegistrationVerifyResponse)
def register_client_verify(
    payload: RegistrationVerifyRequest,
    db: Session = Depends(get_db),
) -> RegistrationVerifyResponse:
    return verify_client_registration(payload, db)


@auth_router.post("/register/admin/start", response_model=RegistrationStartResponse)
def register_admin_start(
    payload: AdminRegisterStartRequest,
    db: Session = Depends(get_db),
) -> RegistrationStartResponse:
    return start_admin_registration(payload, db)


@auth_router.post("/register/admin/verify", response_model=RegistrationVerifyResponse)
def register_admin_verify(
    payload: RegistrationVerifyRequest,
    db: Session = Depends(get_db),
) -> RegistrationVerifyResponse:
    return verify_admin_registration(payload, db)


@auth_router.post("/forgot-password", response_model=SimpleSuccessResponse)
def forgot_password_endpoint(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> SimpleSuccessResponse:
    return forgot_password(payload, db)


@auth_router.post("/reset-password", response_model=SimpleSuccessResponse)
def reset_password_endpoint(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> SimpleSuccessResponse:
    return reset_password(payload, db)


@profile_router.get("/me", response_model=ProfileMeResponse)
def profile_me(
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> ProfileMeResponse:
    return get_profile_me(current_user, db)


@profile_router.patch("/me", response_model=ProfileMeResponse)
def profile_me_update(
    payload: ProfileUpdateRequest,
    current_user=Depends(get_current_profile_user),
    db: Session = Depends(get_db),
) -> ProfileMeResponse:
    return update_profile_me(payload, current_user, db)


@profile_router.get("/me/vehicles", response_model=list[VehicleResponse])
def profile_me_vehicles(
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> list[VehicleResponse]:
    return list_client_vehicles(current_user, db)


@profile_router.post("/me/vehicles", response_model=VehicleResponse, status_code=201)
def profile_me_vehicle_create(
    payload: VehicleCreateRequest,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> VehicleResponse:
    return create_client_vehicle(payload, current_user, db)


@profile_router.patch("/me/vehicles/{vehicle_id}", response_model=VehicleResponse)
def profile_me_vehicle_update(
    vehicle_id: int,
    payload: VehicleUpdateRequest,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> VehicleResponse:
    return update_client_vehicle(vehicle_id, payload, current_user, db)


@profile_router.delete("/me/vehicles/{vehicle_id}", response_model=SimpleSuccessResponse)
def profile_me_vehicle_delete(
    vehicle_id: int,
    current_user=Depends(require_cliente_user),
    db: Session = Depends(get_db),
) -> SimpleSuccessResponse:
    return delete_client_vehicle(vehicle_id, current_user, db)


@profile_router.get("/me/specialties", response_model=list[OperarioSpecialtyResponse])
def profile_me_specialties(
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> list[OperarioSpecialtyResponse]:
    return list_operario_specialties(current_user, db)


@profile_router.put("/me/specialties", response_model=list[OperarioSpecialtyResponse])
def profile_me_specialties_replace(
    payload: OperarioSpecialtyReplaceRequest,
    current_user=Depends(require_operario_user),
    db: Session = Depends(get_db),
) -> list[OperarioSpecialtyResponse]:
    return replace_operario_specialties(payload, current_user, db)


router.include_router(auth_router)
router.include_router(profile_router)
