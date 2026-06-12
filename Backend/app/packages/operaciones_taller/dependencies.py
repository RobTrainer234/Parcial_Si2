from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Query

from app.models import Administrador, Taller, Usuario
from app.packages.seguridad_usuarios.dependencies import (
    forbidden_user_error,
    get_current_user,
    resolve_user_tenant_scope,
)


@dataclass(slots=True)
class WorkshopAdminContext:
    user: Usuario
    administrador: Administrador
    taller: Taller
    tenant_id: int

    @property
    def workshop_id(self) -> int:
        return self.taller.id_taller

    @property
    def admin_persona_id(self) -> int:
        return self.administrador.id_persona


@dataclass(slots=True)
class WorkshopAccessContext:
    user: Usuario
    role: str
    tenant_id: int
    administrador: Administrador | None = None
    taller_ids: tuple[int, ...] = ()

    @property
    def workshop_id(self) -> int:
        if not self.taller_ids:
            raise ValueError("No accessible workshops.")
        return self.taller_ids[0]

    def in_workshop(self, workshop_id: int) -> bool:
        return workshop_id in self.taller_ids


_ADMIN_ROLES = ("ADMINISTRADOR", "ADMIN_SUCURSAL")


def require_workshop_admin_context(
    workshop_id: int | None = Query(None, alias="workshop_id"),
    current_user: Usuario = Depends(get_current_user),
) -> WorkshopAdminContext:
    if current_user.tipo_usuario not in _ADMIN_ROLES:
        raise forbidden_user_error(
            "This endpoint is only available for ADMINISTRADOR or ADMIN_SUCURSAL."
        )

    persona = current_user.persona
    administrador = persona.administrador if persona is not None else None
    if administrador is None or administrador.taller is None:
        raise forbidden_user_error("Administrator actor context is not provisioned.")
    if not administrador.activo or not administrador.taller.activo:
        raise forbidden_user_error("Administrator is not allowed to manage workshop requests.")
    tenant_scope = resolve_user_tenant_scope(current_user)
    if tenant_scope.tenant_id is None:
        raise forbidden_user_error("Administrator workshop is not assigned to a tenant.")
    if workshop_id is not None and workshop_id != administrador.id_taller:
        raise forbidden_user_error("You do not have access to this workshop.")

    return WorkshopAdminContext(
        user=current_user,
        administrador=administrador,
        taller=administrador.taller,
        tenant_id=tenant_scope.tenant_id,
    )


def require_workshop_access(
    current_user: Usuario = Depends(get_current_user),
) -> WorkshopAccessContext:
    role = current_user.tipo_usuario

    if role in _ADMIN_ROLES:
        persona = current_user.persona
        administrador = persona.administrador if persona is not None else None
        if administrador is None or administrador.taller is None:
            raise forbidden_user_error("Administrator actor context is not provisioned.")
        if not administrador.activo or not administrador.taller.activo:
            raise forbidden_user_error("Administrator is not allowed to manage workshop requests.")
        tenant_scope = resolve_user_tenant_scope(current_user)
        if tenant_scope.tenant_id is None:
            raise forbidden_user_error("Administrator workshop is not assigned to a tenant.")

        return WorkshopAccessContext(
            user=current_user,
            role=role,
            tenant_id=tenant_scope.tenant_id,
            administrador=administrador,
            taller_ids=(administrador.id_taller,),
        )

    if role == "ADMIN_GERENTE_SUCURSALES":
        tenant_scope = resolve_user_tenant_scope(current_user)
        if not tenant_scope.workshop_ids or tenant_scope.tenant_id is None:
            raise forbidden_user_error("Manager has no assigned workshops.")
        return WorkshopAccessContext(
            user=current_user,
            role=role,
            tenant_id=tenant_scope.tenant_id,
            taller_ids=tenant_scope.workshop_ids,
        )

    raise forbidden_user_error(
        "This endpoint is only available for administrative roles."
    )


def require_workshop_access_with_workshop_id(
    workshop_id: int | None = Query(None, alias="workshop_id"),
    access: WorkshopAccessContext = Depends(require_workshop_access),
) -> WorkshopAccessContext:
    if workshop_id is not None:
        if not access.in_workshop(workshop_id):
            raise forbidden_user_error("You do not have access to this workshop.")
        return WorkshopAccessContext(
            user=access.user,
            role=access.role,
            tenant_id=access.tenant_id,
            administrador=access.administrador,
            taller_ids=(workshop_id,),
        )
    return access


def require_gerente_context(
    current_user: Usuario = Depends(get_current_user),
) -> WorkshopAccessContext:
    if current_user.tipo_usuario != "ADMIN_GERENTE_SUCURSALES":
        raise forbidden_user_error("This endpoint is only available for ADMIN_GERENTE_SUCURSALES.")

    tenant_scope = resolve_user_tenant_scope(current_user)
    if not tenant_scope.workshop_ids or tenant_scope.tenant_id is None:
        raise forbidden_user_error("Manager has no assigned workshops.")

    return WorkshopAccessContext(
        user=current_user,
        role="ADMIN_GERENTE_SUCURSALES",
        tenant_id=tenant_scope.tenant_id,
        taller_ids=tenant_scope.workshop_ids,
    )


def require_workshop_read_context(
    workshop_id: int | None = Query(None, alias="workshop_id"),
    current_user: Usuario = Depends(get_current_user),
) -> WorkshopAdminContext | WorkshopAccessContext:
    role = current_user.tipo_usuario

    if role in _ADMIN_ROLES:
        persona = current_user.persona
        administrador = persona.administrador if persona is not None else None
        if administrador is None or administrador.taller is None:
            raise forbidden_user_error("Administrator actor context is not provisioned.")
        if not administrador.activo or not administrador.taller.activo:
            raise forbidden_user_error("Administrator is not allowed to manage workshop requests.")
        tenant_scope = resolve_user_tenant_scope(current_user)
        if tenant_scope.tenant_id is None:
            raise forbidden_user_error("Administrator workshop is not assigned to a tenant.")
        if workshop_id is not None and workshop_id != administrador.id_taller:
            raise forbidden_user_error("You do not have access to this workshop.")
        return WorkshopAdminContext(
            user=current_user,
            administrador=administrador,
            taller=administrador.taller,
            tenant_id=tenant_scope.tenant_id,
        )

    if role == "ADMIN_GERENTE_SUCURSALES":
        if workshop_id is None:
            raise forbidden_user_error("workshop_id query parameter is required for ADMIN_GERENTE_SUCURSALES.")
        tenant_scope = resolve_user_tenant_scope(current_user)
        if tenant_scope.tenant_id is None or workshop_id not in tenant_scope.workshop_ids:
            raise forbidden_user_error("You do not have access to this workshop.")
        return WorkshopAccessContext(
            user=current_user,
            role=role,
            tenant_id=tenant_scope.tenant_id,
            taller_ids=(workshop_id,),
        )

    raise forbidden_user_error("This endpoint is only available for administrative roles.")
