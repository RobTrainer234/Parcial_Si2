from __future__ import annotations

from dataclasses import dataclass

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
    Taller,
    Usuario,
    Vehiculo,
)

from .security import decode_token


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class TenantScope:
    role: str
    tenant_id: int | None
    workshop_ids: tuple[int, ...] = ()


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


def _get_taller_tenant_id(taller: Taller | None) -> int | None:
    if taller is None:
        return None
    return taller.id_tenant


def resolve_user_tenant_scope(user: Usuario) -> TenantScope:
    persona = user.persona
    role = user.tipo_usuario

    if role in ("ADMINISTRADOR", "ADMIN_SUCURSAL"):
        administrador = persona.administrador if persona is not None else None
        tenant_id = _get_taller_tenant_id(administrador.taller if administrador is not None else None)
        workshop_id = administrador.id_taller if administrador is not None else None
        return TenantScope(
            role=role,
            tenant_id=tenant_id,
            workshop_ids=((workshop_id,) if workshop_id is not None else ()),
        )

    if role == "OPERARIO":
        operario = persona.operario if persona is not None else None
        tenant_id = _get_taller_tenant_id(operario.taller if operario is not None else None)
        workshop_id = operario.id_taller if operario is not None else None
        return TenantScope(
            role=role,
            tenant_id=tenant_id,
            workshop_ids=((workshop_id,) if workshop_id is not None else ()),
        )

    if role == "ADMIN_GERENTE_SUCURSALES":
        managed_workshops = persona.talleres_gerenciados if persona is not None else []
        active_taller_ids: list[int] = []
        tenant_ids: set[int] = set()
        for managed in managed_workshops:
            taller = managed.taller
            if taller is None or not taller.activo:
                continue
            active_taller_ids.append(managed.id_taller)
            if taller.id_tenant is not None:
                tenant_ids.add(taller.id_tenant)
        tenant_id = next(iter(tenant_ids)) if len(tenant_ids) == 1 else None
        return TenantScope(
            role=role,
            tenant_id=tenant_id,
            workshop_ids=tuple(active_taller_ids),
        )

    return TenantScope(role=role, tenant_id=None, workshop_ids=())


def ensure_user_login_allowed(user: Usuario) -> Usuario:
    if not user.activo:
        raise forbidden_user_error("User account is inactive.")

    persona = user.persona
    tenant_scope = resolve_user_tenant_scope(user)

    if user.tipo_usuario in ("ADMINISTRADOR", "ADMIN_SUCURSAL"):
        administrador = persona.administrador if persona is not None else None
        if administrador is None or administrador.taller is None:
            raise forbidden_user_error("User is not allowed to perform this action.")
        if not administrador.activo or not administrador.taller.activo:
            raise forbidden_user_error("User is not allowed to perform this action.")
        if tenant_scope.tenant_id is None:
            raise forbidden_user_error("User workshop is not assigned to a tenant.")

    elif user.tipo_usuario == "ADMIN_GERENTE_SUCURSALES":
        talleres_gerenciados = persona.talleres_gerenciados if persona is not None else None
        if not talleres_gerenciados:
            raise forbidden_user_error("User is not allowed to perform this action.")
        if not tenant_scope.workshop_ids or tenant_scope.tenant_id is None:
            raise forbidden_user_error("Manager workshops are not provisioned for a single tenant.")

    elif user.tipo_usuario == "OPERARIO":
        operario = persona.operario if persona is not None else None
        if operario is None or operario.taller is None:
            raise forbidden_user_error("User is not allowed to perform this action.")
        if not operario.activo or not operario.taller.activo:
            raise forbidden_user_error("User is not allowed to perform this action.")
        if tenant_scope.tenant_id is None:
            raise forbidden_user_error("Operario workshop is not assigned to a tenant.")

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
        "tenant_id": None,
    }

    persona = user.persona
    if persona is None:
        return actor_context

    if persona.cliente is not None:
        actor_context["cliente_persona_id"] = persona.cliente.id_persona
    if persona.administrador is not None:
        actor_context["administrador_persona_id"] = persona.administrador.id_persona
        actor_context["taller_id"] = persona.administrador.id_taller
        actor_context["tenant_id"] = persona.administrador.taller.id_tenant
    if persona.operario is not None:
        actor_context["operario_id"] = persona.operario.id_persona
        actor_context["taller_id"] = persona.operario.id_taller
        actor_context["tenant_id"] = persona.operario.taller.id_tenant
    if persona.talleres_gerenciados:
        tenant_scope = resolve_user_tenant_scope(user)
        actor_context["taller_ids"] = list(tenant_scope.workshop_ids)
        actor_context["tenant_id"] = tenant_scope.tenant_id

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


def get_user_from_access_token(token: str, db: Session) -> Usuario:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    try:
        payload = decode_token(token, expected_type="access")
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


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    return get_user_from_access_token(credentials.credentials, db)


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
