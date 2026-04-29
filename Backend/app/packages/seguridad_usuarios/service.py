from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    Administrador,
    Cliente,
    Color,
    Especialidad,
    Marca,
    Modelo,
    OperarioEspecialidad,
    Persona,
    RegistroPendiente,
    Taller,
    Usuario,
    Vehiculo,
)

from .dependencies import (
    build_home_hint,
    ensure_user_login_allowed,
    profile_context_query,
    serialize_user_profile,
    user_context_query,
)
from .schemas import (
    AdminRegisterStartRequest,
    ClientRegisterStartRequest,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    OperarioSpecialtyItem,
    OperarioSpecialtyReplaceRequest,
    OperarioSpecialtyResponse,
    PendingAdminRegistrationPayload,
    PendingClientRegistrationPayload,
    PersonaProfileResponse,
    ProfileMeResponse,
    ProfileUpdateRequest,
    RegistrationStartResponse,
    RegistrationVerifyRequest,
    RegistrationVerifyResponse,
    SimpleSuccessResponse,
    UserProfileResponse,
    VehicleCreateRequest,
    VehicleRegistrationItem,
    VehicleResponse,
    VehicleUpdateRequest,
)
from .security import (
    build_verification_code_digest,
    create_access_token,
    create_registration_token,
    decode_token,
    generate_verification_code,
    hash_password,
    utc_now,
    verify_password,
)


settings = get_settings()
LOCAL_ENVIRONMENTS = {"local", "development", "dev"}
DUMMY_PASSWORD_HASH = hash_password("ProyectoSI2-invalid-password")


def _is_local_environment() -> bool:
    return settings.environment.lower() in LOCAL_ENVIRONMENTS


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_phone(phone: str) -> str:
    return phone.strip()


def _normalize_plate(plate: str) -> str:
    return plate.strip().upper()


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_text(value)
    return normalized or None


def _normalize_optional_phone(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_phone(value)
    return normalized or None


def _normalize_vehicle_payload(vehicle: VehicleRegistrationItem) -> dict[str, object]:
    return {
        "placa": _normalize_plate(vehicle.placa),
        "anio": vehicle.anio,
        "marca_nombre": _normalize_text(vehicle.marca_nombre),
        "modelo_nombre": _normalize_text(vehicle.modelo_nombre),
        "color_nombre": _normalize_text(vehicle.color_nombre),
    }


def _user_by_email_query(email: str):
    return user_context_query().where(func.lower(Usuario.email) == _normalize_email(email))


def _get_user_by_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(_user_by_email_query(email))


def _get_profile_user(db: Session, user_id: int) -> Usuario:
    user = db.scalar(profile_context_query().where(Usuario.id_usuario == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile user not found.",
        )
    return user


def _reset_lockout_state(user: Usuario) -> None:
    user.intentos = 0
    user.bloqueado = False
    user.bloqueado_hasta = None


def _build_login_response(user: Usuario) -> LoginResponse:
    user_profile = UserProfileResponse.model_validate(serialize_user_profile(user))
    return LoginResponse(
        access_token=create_access_token(
            user_id=user.id_usuario,
            role=user.tipo_usuario,
            home_hint=user_profile.home_hint,
        ),
        token_type="bearer",
        role=user.tipo_usuario,
        user=user_profile,
        actor_context=user_profile.actor_context,
        home_hint=user_profile.home_hint,
    )


def _ensure_email_unique(db: Session, email: str) -> None:
    exists = db.scalar(
        select(Usuario.id_usuario).where(func.lower(Usuario.email) == _normalize_email(email))
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")


def _ensure_ci_unique(db: Session, ci: str) -> None:
    exists = db.scalar(select(Persona.id_persona).where(Persona.ci == _normalize_text(ci)))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CI already exists.")


def _ensure_phone_unique(
    db: Session,
    telefono: str | None,
    *,
    exclude_persona_id: int | None = None,
) -> None:
    normalized_phone = _normalize_optional_phone(telefono)
    if normalized_phone is None:
        return

    query = select(Persona.id_persona).where(Persona.telefono == normalized_phone)
    if exclude_persona_id is not None:
        query = query.where(Persona.id_persona != exclude_persona_id)

    exists = db.scalar(query)
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already exists.")


def _ensure_vehicle_plate_unique(
    db: Session,
    placa: str,
    *,
    exclude_vehicle_id: int | None = None,
) -> None:
    normalized_plate = _normalize_plate(placa)
    query = select(Vehiculo.id_vehiculo).where(func.upper(Vehiculo.placa) == normalized_plate)
    if exclude_vehicle_id is not None:
        query = query.where(Vehiculo.id_vehiculo != exclude_vehicle_id)

    exists = db.scalar(query)
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle plate already exists.",
        )


def _ensure_vehicle_plates_unique(db: Session, vehicles: list[VehicleRegistrationItem]) -> None:
    normalized_plates = [_normalize_plate(vehicle.placa) for vehicle in vehicles]
    if len(normalized_plates) != len(set(normalized_plates)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle plates must be unique inside the request.",
        )

    existing_plates = list(
        db.scalars(select(Vehiculo.placa).where(func.upper(Vehiculo.placa).in_(normalized_plates)))
    )
    if existing_plates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vehicle plate already exists: {existing_plates[0]}",
        )


def _build_client_pending_payload(
    payload: ClientRegisterStartRequest,
) -> PendingClientRegistrationPayload:
    return PendingClientRegistrationPayload(
        nombre=_normalize_text(payload.nombre),
        apellido=_normalize_text(payload.apellido),
        ci=_normalize_text(payload.ci),
        telefono=_normalize_phone(payload.telefono),
        direccion=_normalize_optional_text(payload.direccion),
        email=_normalize_email(payload.email),
        password_hash=hash_password(payload.password),
        vehicles=[
            VehicleRegistrationItem.model_validate(_normalize_vehicle_payload(vehicle))
            for vehicle in payload.vehicles
        ],
    )


def _build_admin_pending_payload(
    payload: AdminRegisterStartRequest,
) -> PendingAdminRegistrationPayload:
    return PendingAdminRegistrationPayload(
        nombre=_normalize_text(payload.nombre),
        apellido=_normalize_text(payload.apellido),
        ci=_normalize_text(payload.ci),
        telefono=_normalize_phone(payload.telefono),
        direccion=_normalize_optional_text(payload.direccion),
        email=_normalize_email(payload.email),
        password_hash=hash_password(payload.password),
        workshop=payload.workshop.model_copy(
            update={
                "nombre_comercial": _normalize_text(payload.workshop.nombre_comercial),
                "descripcion": _normalize_optional_text(payload.workshop.descripcion),
            }
        ),
    )


def _build_registration_start_response(
    *,
    role: str,
    token: str,
    expires_at: datetime,
    verification_code: str,
) -> RegistrationStartResponse:
    return RegistrationStartResponse(
        status="verification_pending",
        role=role,
        registration_token=token,
        expires_at=expires_at,
        debug_verification_code=verification_code if _is_local_environment() else None,
    )


def _create_pending_registration(
    *,
    db: Session,
    flow: str,
    payload_json: dict[str, object],
    verification_code: str,
) -> RegistrationStartResponse:
    now = utc_now()
    expires_at = now + timedelta(minutes=settings.registration_token_expire_minutes)
    pending = RegistroPendiente(
        flujo=flow,
        payload_json=payload_json,
        verification_code_digest=build_verification_code_digest(verification_code),
        expires_at=expires_at,
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    token = create_registration_token(
        pending_registration_id=pending.id_registro_pendiente,
        flow=flow,
        expires_at=expires_at,
    )
    return _build_registration_start_response(
        role=flow,
        token=token,
        expires_at=expires_at,
        verification_code=verification_code,
    )


def _decode_pending_registration_token(
    *,
    token: str,
    expected_flow: str,
) -> int:
    try:
        token_payload = decode_token(token, expected_type="registration")
    except (InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration token.",
        ) from None

    if token_payload.get("flow") != expected_flow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration token flow mismatch.",
        )

    try:
        return int(token_payload["pending_registration_id"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration token is invalid.",
        ) from None


def _load_pending_registration_for_verify(
    *,
    db: Session,
    pending_registration_id: int,
    expected_flow: str,
    verification_code: str,
) -> RegistroPendiente:
    pending = db.scalar(
        select(RegistroPendiente)
        .where(RegistroPendiente.id_registro_pendiente == pending_registration_id)
        .with_for_update()
    )
    if pending is None or pending.flujo != expected_flow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending registration not found.",
        )

    now = utc_now()
    if pending.consumed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending registration was already consumed.",
        )
    if pending.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending registration expired.",
        )
    if pending.verification_code_digest != build_verification_code_digest(
        verification_code.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    return pending


def _get_or_create_marca(db: Session, nombre: str) -> Marca:
    normalized_name = _normalize_text(nombre)
    marca = db.scalar(select(Marca).where(func.lower(Marca.nombre) == normalized_name.lower()))
    if marca is not None:
        return marca

    marca = Marca(nombre=normalized_name)
    db.add(marca)
    db.flush()
    return marca


def _get_or_create_modelo(db: Session, *, marca: Marca, nombre: str) -> Modelo:
    normalized_name = _normalize_text(nombre)
    modelo = db.scalar(
        select(Modelo).where(
            Modelo.id_marca == marca.id_marca,
            func.lower(Modelo.nombre) == normalized_name.lower(),
        )
    )
    if modelo is not None:
        return modelo

    modelo = Modelo(id_marca=marca.id_marca, nombre=normalized_name)
    db.add(modelo)
    db.flush()
    return modelo


def _get_or_create_color(db: Session, nombre: str) -> Color:
    normalized_name = _normalize_text(nombre)
    color = db.scalar(select(Color).where(func.lower(Color.nombre) == normalized_name.lower()))
    if color is not None:
        return color

    color = Color(nombre=normalized_name)
    db.add(color)
    db.flush()
    return color


def _resolve_vehicle_catalogs(
    db: Session,
    *,
    marca_nombre: str,
    modelo_nombre: str,
    color_nombre: str,
) -> tuple[Modelo, Color]:
    marca = _get_or_create_marca(db, marca_nombre)
    modelo = _get_or_create_modelo(db, marca=marca, nombre=modelo_nombre)
    color = _get_or_create_color(db, color_nombre)
    return modelo, color


def _serialize_vehicle(vehicle: Vehiculo) -> VehicleResponse:
    return VehicleResponse(
        id_vehiculo=vehicle.id_vehiculo,
        placa=vehicle.placa,
        anio=vehicle.anio,
        marca_nombre=vehicle.modelo.marca.nombre,
        modelo_nombre=vehicle.modelo.nombre,
        color_nombre=vehicle.color.nombre,
    )


def _serialize_operario_specialty(association: OperarioEspecialidad) -> OperarioSpecialtyResponse:
    return OperarioSpecialtyResponse(
        id_especialidad=association.id_especialidad,
        nombre=association.especialidad.nombre,
        anios_experiencia=association.anios_experiencia,
        certificacion_url=association.certificacion_url,
    )


def _load_client_vehicles(db: Session, *, persona_id: int) -> list[Vehiculo]:
    return list(
        db.scalars(
            select(Vehiculo)
            .where(Vehiculo.id_persona == persona_id)
            .order_by(Vehiculo.id_vehiculo)
        )
    )


def _load_operario_specialties(db: Session, *, persona_id: int) -> list[OperarioEspecialidad]:
    return list(
        db.scalars(
            select(OperarioEspecialidad)
            .where(OperarioEspecialidad.id_persona == persona_id)
            .order_by(OperarioEspecialidad.id_especialidad)
        )
    )


def _build_profile_response(user: Usuario, *, db: Session | None = None) -> ProfileMeResponse:
    persona = user.persona
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona profile not found.",
        )

    vehicles: list[VehicleResponse] | None = None
    specialties: list[OperarioSpecialtyResponse] | None = None

    if user.tipo_usuario == "CLIENTE" and persona.cliente is not None:
        vehicle_rows = (
            _load_client_vehicles(db, persona_id=persona.id_persona)
            if db is not None
            else sorted(persona.cliente.vehiculos, key=lambda item: item.id_vehiculo)
        )
        vehicles = [
            _serialize_vehicle(vehicle)
            for vehicle in vehicle_rows
        ]
    elif user.tipo_usuario == "OPERARIO" and persona.operario is not None:
        specialty_rows = (
            _load_operario_specialties(db, persona_id=persona.id_persona)
            if db is not None
            else sorted(
                persona.operario.especialidades,
                key=lambda item: item.id_especialidad,
            )
        )
        specialties = [
            _serialize_operario_specialty(association)
            for association in specialty_rows
        ]

    return ProfileMeResponse(
        persona=PersonaProfileResponse(
            nombre=persona.nombre,
            apellido=persona.apellido,
            ci=persona.ci,
            telefono=persona.telefono,
            direccion=persona.direccion,
        ),
        user=UserProfileResponse.model_validate(serialize_user_profile(user)),
        vehicles=vehicles,
        specialties=specialties,
    )


def _get_client_owned_vehicle(db: Session, *, vehicle_id: int, persona_id: int) -> Vehiculo:
    vehicle = db.scalar(
        select(Vehiculo).where(
            Vehiculo.id_vehiculo == vehicle_id,
            Vehiculo.id_persona == persona_id,
        )
    )
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )
    return vehicle


def _validate_patch_string(value: str | None, *, field_name: str) -> str:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot be null.",
        )
    return _normalize_text(value)


def login_user(payload: LoginRequest, db: Session) -> LoginResponse:
    user = _get_user_by_email(db, payload.email)
    now = utc_now()

    if user is not None and user.bloqueado_hasta is not None and user.bloqueado_hasta <= now:
        _reset_lockout_state(user)

    if user is not None and user.bloqueado_hasta is not None and user.bloqueado_hasta > now:
        remaining_seconds = max(int((user.bloqueado_hasta - now).total_seconds()), 1)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "message": "User is temporarily blocked.",
                "retry_after_seconds": remaining_seconds,
                "blocked_until": user.bloqueado_hasta.isoformat(),
            },
        )

    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, password_hash)

    if user is None or not password_valid:
        if user is not None:
            user.intentos += 1
            if user.intentos >= 3:
                user.bloqueado = True
                user.bloqueado_hasta = now + timedelta(minutes=settings.lockout_minutes)
                # Se conserva el valor 3 mientras dura el bloqueo; al expirar se reinicia el contador.
                user.intentos = 3
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    _reset_lockout_state(user)
    try:
        ensure_user_login_allowed(user)
    except HTTPException:
        db.commit()
        raise

    user.ultimo_acceso = now
    db.commit()
    db.refresh(user)

    return _build_login_response(user)


def get_me(current_user: Usuario) -> UserProfileResponse:
    return UserProfileResponse.model_validate(serialize_user_profile(current_user))


def logout_user() -> LogoutResponse:
    return LogoutResponse(
        status="ok",
        message="Logout successful. Discard the bearer token on the client side.",
    )


def start_client_registration(
    payload: ClientRegisterStartRequest,
    db: Session,
) -> RegistrationVerifyResponse:
    _ensure_email_unique(db, payload.email)
    _ensure_ci_unique(db, payload.ci)
    _ensure_phone_unique(db, payload.telefono)
    _ensure_vehicle_plates_unique(db, payload.vehicles)

    try:
        registration_data = _build_client_pending_payload(payload)

        persona = Persona(
            nombre=registration_data.nombre,
            apellido=registration_data.apellido,
            ci=registration_data.ci,
            telefono=registration_data.telefono,
            direccion=registration_data.direccion,
        )
        db.add(persona)
        db.flush()

        db.add(
            Usuario(
                id_persona=persona.id_persona,
                email=_normalize_email(registration_data.email),
                password_hash=registration_data.password_hash,
                tipo_usuario="CLIENTE",
                activo=True,
            )
        )
        db.add(Cliente(id_persona=persona.id_persona))
        db.flush()

        for vehicle in registration_data.vehicles:
            modelo, color = _resolve_vehicle_catalogs(
                db,
                marca_nombre=vehicle.marca_nombre,
                modelo_nombre=vehicle.modelo_nombre,
                color_nombre=vehicle.color_nombre,
            )
            db.add(
                Vehiculo(
                    placa=_normalize_plate(vehicle.placa),
                    id_modelo=modelo.id_modelo,
                    anio=vehicle.anio,
                    id_color=color.id_color,
                    id_persona=persona.id_persona,
                )
            )

        db.commit()

        created_user = _get_user_by_email(db, registration_data.email)
        if created_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Client registration did not persist user.",
            )
        if not verify_password(payload.password, created_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Client registration stored invalid credentials.",
            )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client registration conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Client registration failed.",
        ) from exc

    return RegistrationVerifyResponse(
        status="created",
        role="CLIENTE",
        home_hint=build_home_hint("CLIENTE"),
        created_vehicle_count=len(payload.vehicles),
    )


def verify_client_registration(
    payload: RegistrationVerifyRequest,
    db: Session,
) -> RegistrationVerifyResponse:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Client registration no longer requires verification.",
    )


def start_admin_registration(
    payload: AdminRegisterStartRequest,
    db: Session,
) -> RegistrationStartResponse:
    _ensure_email_unique(db, payload.email)
    _ensure_ci_unique(db, payload.ci)
    _ensure_phone_unique(db, payload.telefono)

    verification_code = generate_verification_code()
    pending_payload = _build_admin_pending_payload(payload)
    try:
        return _create_pending_registration(
            db=db,
            flow="ADMINISTRADOR",
            payload_json=pending_payload.model_dump(mode="json"),
            verification_code=verification_code,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin registration could not be started.",
        ) from exc


def verify_admin_registration(
    payload: RegistrationVerifyRequest,
    db: Session,
) -> RegistrationVerifyResponse:
    pending_registration_id = _decode_pending_registration_token(
        token=payload.registration_token,
        expected_flow="ADMINISTRADOR",
    )

    try:
        with db.begin():
            pending = _load_pending_registration_for_verify(
                db=db,
                pending_registration_id=pending_registration_id,
                expected_flow="ADMINISTRADOR",
                verification_code=payload.verification_code,
            )
            registration_data = PendingAdminRegistrationPayload.model_validate(
                pending.payload_json
            )

            _ensure_email_unique(db, registration_data.email)
            _ensure_ci_unique(db, registration_data.ci)
            _ensure_phone_unique(db, registration_data.telefono)

            persona = Persona(
                nombre=registration_data.nombre,
                apellido=registration_data.apellido,
                ci=registration_data.ci,
                telefono=registration_data.telefono,
                direccion=registration_data.direccion,
            )
            db.add(persona)
            db.flush()

            taller = Taller(
                nombre_comercial=registration_data.workshop.nombre_comercial,
                descripcion=registration_data.workshop.descripcion,
                latitud=registration_data.workshop.latitud,
                longitud=registration_data.workshop.longitud,
                radio_accion_km=registration_data.workshop.radio_accion_km,
            )
            db.add(taller)
            db.flush()

            db.add(
                Usuario(
                    id_persona=persona.id_persona,
                    email=_normalize_email(registration_data.email),
                    password_hash=registration_data.password_hash,
                    tipo_usuario="ADMINISTRADOR",
                )
            )
            db.add(
                Administrador(
                    id_persona=persona.id_persona,
                    id_taller=taller.id_taller,
                )
            )

            pending.consumed_at = utc_now()
    except HTTPException:
        raise
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin registration conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin registration failed.",
        ) from exc

    return RegistrationVerifyResponse(
        status="created",
        role="ADMINISTRADOR",
        home_hint=build_home_hint("ADMINISTRADOR"),
    )


def get_profile_me(current_user: Usuario, db: Session) -> ProfileMeResponse:
    user = _get_profile_user(db, current_user.id_usuario)
    return _build_profile_response(user, db=db)


def update_profile_me(
    payload: ProfileUpdateRequest,
    current_user: Usuario,
    db: Session,
) -> ProfileMeResponse:
    user = _get_profile_user(db, current_user.id_usuario)
    persona = user.persona

    if "nombre" in payload.model_fields_set:
        persona.nombre = _validate_patch_string(payload.nombre, field_name="nombre")
    if "apellido" in payload.model_fields_set:
        persona.apellido = _validate_patch_string(payload.apellido, field_name="apellido")
    if "telefono" in payload.model_fields_set:
        normalized_phone = _normalize_optional_phone(payload.telefono)
        _ensure_phone_unique(db, normalized_phone, exclude_persona_id=persona.id_persona)
        persona.telefono = normalized_phone
    if "direccion" in payload.model_fields_set:
        persona.direccion = _normalize_optional_text(payload.direccion)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile update conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile could not be updated.",
        ) from exc

    return _build_profile_response(_get_profile_user(db, current_user.id_usuario), db=db)


def list_client_vehicles(current_user: Usuario, db: Session) -> list[VehicleResponse]:
    user = _get_profile_user(db, current_user.id_usuario)
    return [
        _serialize_vehicle(vehicle)
        for vehicle in _load_client_vehicles(db, persona_id=user.id_persona)
    ]


def create_client_vehicle(
    payload: VehicleCreateRequest,
    current_user: Usuario,
    db: Session,
) -> VehicleResponse:
    profile_user = _get_profile_user(db, current_user.id_usuario)
    persona = profile_user.persona
    _ensure_vehicle_plate_unique(db, payload.placa)

    try:
        modelo, color = _resolve_vehicle_catalogs(
            db,
            marca_nombre=payload.marca_nombre,
            modelo_nombre=payload.modelo_nombre,
            color_nombre=payload.color_nombre,
        )
        vehicle = Vehiculo(
            placa=_normalize_plate(payload.placa),
            id_modelo=modelo.id_modelo,
            anio=payload.anio,
            id_color=color.id_color,
            id_persona=persona.id_persona,
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vehicle could not be created.",
        ) from exc

    return _serialize_vehicle(vehicle)


def update_client_vehicle(
    vehicle_id: int,
    payload: VehicleUpdateRequest,
    current_user: Usuario,
    db: Session,
) -> VehicleResponse:
    current_profile_user = _get_profile_user(db, current_user.id_usuario)
    vehicle = _get_client_owned_vehicle(
        db,
        vehicle_id=vehicle_id,
        persona_id=current_profile_user.id_persona,
    )

    new_plate = vehicle.placa
    if "placa" in payload.model_fields_set:
        if payload.placa is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="placa cannot be null.",
            )
        new_plate = _normalize_plate(payload.placa)
        if new_plate != vehicle.placa:
            _ensure_vehicle_plate_unique(db, new_plate, exclude_vehicle_id=vehicle.id_vehiculo)
            vehicle.placa = new_plate

    if "anio" in payload.model_fields_set:
        if payload.anio is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="anio cannot be null.",
            )
        vehicle.anio = payload.anio

    marca_nombre = (
        _validate_patch_string(payload.marca_nombre, field_name="marca_nombre")
        if "marca_nombre" in payload.model_fields_set
        else vehicle.modelo.marca.nombre
    )
    modelo_nombre = (
        _validate_patch_string(payload.modelo_nombre, field_name="modelo_nombre")
        if "modelo_nombre" in payload.model_fields_set
        else vehicle.modelo.nombre
    )
    color_nombre = (
        _validate_patch_string(payload.color_nombre, field_name="color_nombre")
        if "color_nombre" in payload.model_fields_set
        else vehicle.color.nombre
    )

    try:
        modelo, color = _resolve_vehicle_catalogs(
            db,
            marca_nombre=marca_nombre,
            modelo_nombre=modelo_nombre,
            color_nombre=color_nombre,
        )
        vehicle.id_modelo = modelo.id_modelo
        vehicle.id_color = color.id_color
        db.commit()
        db.refresh(vehicle)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vehicle could not be updated.",
        ) from exc

    return _serialize_vehicle(vehicle)


def delete_client_vehicle(
    vehicle_id: int,
    current_user: Usuario,
    db: Session,
) -> SimpleSuccessResponse:
    vehicle = _get_client_owned_vehicle(
        db,
        vehicle_id=vehicle_id,
        persona_id=current_user.id_persona,
    )
    try:
        db.delete(vehicle)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle cannot be deleted because it is still referenced.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vehicle could not be deleted.",
        ) from exc

    return SimpleSuccessResponse(status="ok", message="Vehicle deleted successfully.")


def list_operario_specialties(
    current_user: Usuario,
    db: Session,
) -> list[OperarioSpecialtyResponse]:
    user = _get_profile_user(db, current_user.id_usuario)
    return [
        _serialize_operario_specialty(association)
        for association in _load_operario_specialties(db, persona_id=user.id_persona)
    ]


def replace_operario_specialties(
    payload: OperarioSpecialtyReplaceRequest,
    current_user: Usuario,
    db: Session,
) -> list[OperarioSpecialtyResponse]:
    user = _get_profile_user(db, current_user.id_usuario)
    operario = user.persona.operario

    specialty_ids = [item.id_especialidad for item in payload.specialties]
    if len(specialty_ids) != len(set(specialty_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specialty ids must be unique inside the request.",
        )

    existing_specialty_ids = set(
        db.scalars(
            select(Especialidad.id_especialidad).where(Especialidad.id_especialidad.in_(specialty_ids))
        )
    )
    missing_specialty_ids = sorted(set(specialty_ids) - existing_specialty_ids)
    if missing_specialty_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown specialty ids: {missing_specialty_ids}",
        )

    current_by_specialty_id = {
        association.id_especialidad: association for association in operario.especialidades
    }
    requested_ids = set(specialty_ids)

    try:
        for association in list(operario.especialidades):
            if association.id_especialidad not in requested_ids:
                db.delete(association)

        for item in payload.specialties:
            normalized_certification_url = _normalize_optional_text(item.certificacion_url)
            association = current_by_specialty_id.get(item.id_especialidad)
            if association is None:
                db.add(
                    OperarioEspecialidad(
                        id_persona=operario.id_persona,
                        id_especialidad=item.id_especialidad,
                        anios_experiencia=item.anios_experiencia,
                        certificacion_url=normalized_certification_url,
                    )
                )
            else:
                association.anios_experiencia = item.anios_experiencia
                association.certificacion_url = normalized_certification_url

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Specialties conflict with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Specialties could not be updated.",
        ) from exc

    return [
        _serialize_operario_specialty(association)
        for association in _load_operario_specialties(db, persona_id=current_user.id_persona)
    ]
