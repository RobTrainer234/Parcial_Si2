from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.session import get_db
from app.models import (
    Administrador,
    Cliente,
    GerenteTaller,
    Modelo,
    Operario,
    OperarioEspecialidad,
    Persona,
    Usuario,
    Vehiculo,
)

from .security import decode_token


bearer_scheme = HTTPBearer(auto_error=False)


def user_context_query():
    return select(Usuario).options(
        joinedload(Usuario.persona)
        .joinedload(Persona.administrador)
        .joinedload(Administrador.taller),
        joinedload(Usuario.persona)
        .joinedload(Persona.operario)
        .joinedload(Operario.taller),
        joinedload(Usuario.persona).joinedload(Persona.cliente),
        joinedload(Usuario.persona)
        .selectinload(Persona.talleres_gerenciados)
        .joinedload(GerenteTaller.taller),
    )


def profile_context_query():
    return select(Usuario).options(
        joinedload(Usuario.persona)
        .joinedload(Persona.administrador)
        .joinedload(Administrador.taller),
        joinedload(Usuario.persona)
        .joinedload(Persona.operario)
        .joinedload(Operario.taller),
        joinedload(Usuario.persona).joinedload(Persona.cliente),
        joinedload(Usuario.persona)
        .selectinload(Persona.talleres_gerenciados)
        .joinedload(GerenteTaller.taller),
        joinedload(Usuario.persona)
        .joinedload(Persona.cliente)
        .selectinload(Cliente.vehiculos)
        .joinedload(Vehiculo.modelo)
        .joinedload(Modelo.marca),
        joinedload(Usuario.persona)
        .joinedload(Persona.cliente)
        .selectinload(Cliente.vehiculos)
        .joinedload(Vehiculo.color),
        joinedload(Usuario.persona)
        .joinedload(Persona.operario)
        .selectinload(Operario.especialidades)
        .joinedload(OperarioEspecialidad.especialidad),
    )


def forbidden_user_error(message: str = "User is not allowed to perform this action.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def ensure_user_login_allowed(user: Usuario) -> Usuario:
    if not user.activo:
        raise forbidden_user_error("User account is inactive.")

    persona = user.persona

    if user.tipo_usuario in ("ADMINISTRADOR", "ADMIN_SUCURSAL"):
        administrador = persona.administrador if persona is not None else None
        if administrador is None or administrador.taller is None:
            raise forbidden_user_error("User is not allowed to perform this action.")
        if not administrador.activo or not administrador.taller.activo:
            raise forbidden_user_error("User is not allowed to perform this action.")

    elif user.tipo_usuario == "ADMIN_GERENTE_SUCURSALES":
        talleres_gerenciados = persona.talleres_gerenciados if persona is not None else None
        if not talleres_gerenciados:
            raise forbidden_user_error("User is not allowed to perform this action.")

    elif user.tipo_usuario == "OPERARIO":
        operario = persona.operario if persona is not None else None
        if operario is None or operario.taller is None:
            raise forbidden_user_error("User is not allowed to perform this action.")
        if not operario.activo or not operario.taller.activo:
            raise forbidden_user_error("User is not allowed to perform this action.")

    return user


def ensure_profile_access_allowed(user: Usuario) -> Usuario:
    ensure_user_login_allowed(user)
    allowed_roles = {"CLIENTE", "OPERARIO", "ADMINISTRADOR", "ADMIN_SUCURSAL", "ADMIN_GERENTE_SUCURSALES"}
    if user.tipo_usuario not in allowed_roles:
        raise forbidden_user_error("This profile endpoint is not available for the current role.")

    persona = user.persona
    if user.tipo_usuario == "CLIENTE" and (persona is None or persona.cliente is None):
        raise forbidden_user_error("Client profile is not provisioned.")
    if user.tipo_usuario == "OPERARIO" and (persona is None or persona.operario is None):
        raise forbidden_user_error("Operario profile is not provisioned.")
    if user.tipo_usuario in ("ADMINISTRADOR", "ADMIN_SUCURSAL") and (
        persona is None or persona.administrador is None or persona.administrador.taller is None
    ):
        raise forbidden_user_error("Administrator profile is not provisioned.")
    if user.tipo_usuario == "ADMIN_GERENTE_SUCURSALES" and (
        persona is None or not persona.talleres_gerenciados
    ):
        raise forbidden_user_error("Manager profile is not provisioned.")

    return user


def build_actor_context(user: Usuario) -> dict[str, int | None]:
    actor_context: dict[str, int | None] = {
        "cliente_persona_id": None,
        "administrador_persona_id": None,
        "operario_id": None,
        "taller_id": None,
        "taller_ids": None,
    }

    persona = user.persona
    if persona is None:
        return actor_context

    if persona.cliente is not None:
        actor_context["cliente_persona_id"] = persona.cliente.id_persona
    if persona.administrador is not None:
        actor_context["administrador_persona_id"] = persona.administrador.id_persona
        actor_context["taller_id"] = persona.administrador.id_taller
    if persona.operario is not None:
        actor_context["operario_id"] = persona.operario.id_persona
        actor_context["taller_id"] = persona.operario.id_taller
    if persona.talleres_gerenciados:
        actor_context["taller_ids"] = [gt.id_taller for gt in persona.talleres_gerenciados]

    return actor_context


def build_home_hint(role: str) -> str:
    mapping = {
        "CLIENTE": "mobile_client_dashboard",
        "ADMINISTRADOR": "web_admin_dashboard",
        "ADMIN_SUCURSAL": "web_admin_dashboard",
        "ADMIN_GERENTE_SUCURSALES": "web_admin_dashboard",
        "OPERARIO": "mobile_operario_dashboard",
        "SUPER_ADMIN": "admin_global_dashboard",
    }
    return mapping.get(role, "web_admin_dashboard")


def serialize_user_profile(user: Usuario) -> dict[str, object]:
    persona = user.persona
    return {
        "user_id": user.id_usuario,
        "persona_id": persona.id_persona if persona else user.id_persona,
        "role": user.tipo_usuario,
        "email": user.email,
        "phone": persona.telefono if persona else None,
        "actor_context": build_actor_context(user),
        "home_hint": build_home_hint(user.tipo_usuario),
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from None

    user = db.scalar(user_context_query().where(Usuario.id_usuario == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found.",
        )

    return ensure_user_login_allowed(user)


def get_current_profile_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    return ensure_profile_access_allowed(current_user)


def require_cliente_user(current_user: Usuario = Depends(get_current_profile_user)) -> Usuario:
    if current_user.tipo_usuario != "CLIENTE":
        raise forbidden_user_error("This endpoint is only available for CLIENTE.")
    return current_user


def require_operario_user(current_user: Usuario = Depends(get_current_profile_user)) -> Usuario:
    if current_user.tipo_usuario != "OPERARIO":
        raise forbidden_user_error("This endpoint is only available for OPERARIO.")
    return current_user
