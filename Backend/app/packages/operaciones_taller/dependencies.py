from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Query

from app.models import Administrador, Taller, Usuario
from app.packages.seguridad_usuarios.dependencies import (
    forbidden_user_error,
    get_current_user,
)


@dataclass(slots=True)
class WorkshopAdminContext:
    user: Usuario
    administrador: Administrador
    taller: Taller

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

    return WorkshopAdminContext(
        user=current_user,
        administrador=administrador,
        taller=administrador.taller,
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

        return WorkshopAccessContext(
            user=current_user,
            role=role,
            administrador=administrador,
            taller_ids=(administrador.id_taller,),
        )

    if role == "ADMIN_GERENTE_SUCURSALES":
        persona = current_user.persona
        if persona is None or not persona.talleres_gerenciados:
            raise forbidden_user_error("Manager has no assigned workshops.")

        taller_ids = tuple(gt.id_taller for gt in persona.talleres_gerenciados)
        return WorkshopAccessContext(
            user=current_user,
            role=role,
            taller_ids=taller_ids,
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
            administrador=access.administrador,
            taller_ids=(workshop_id,),
        )
    return access


def require_gerente_context(
    current_user: Usuario = Depends(get_current_user),
) -> WorkshopAccessContext:
    if current_user.tipo_usuario != "ADMIN_GERENTE_SUCURSALES":
        raise forbidden_user_error("This endpoint is only available for ADMIN_GERENTE_SUCURSALES.")

    persona = current_user.persona
    if persona is None or not persona.talleres_gerenciados:
        raise forbidden_user_error("Manager has no assigned workshops.")

    taller_ids = tuple(gt.id_taller for gt in persona.talleres_gerenciados)
    return WorkshopAccessContext(
        user=current_user,
        role="ADMIN_GERENTE_SUCURSALES",
        taller_ids=taller_ids,
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
        return WorkshopAdminContext(
            user=current_user,
            administrador=administrador,
            taller=administrador.taller,
        )

    if role == "ADMIN_GERENTE_SUCURSALES":
        if workshop_id is None:
            raise forbidden_user_error("workshop_id query parameter is required for ADMIN_GERENTE_SUCURSALES.")
        persona = current_user.persona
        if persona is None or not any(gt.id_taller == workshop_id for gt in persona.talleres_gerenciados):
            raise forbidden_user_error("You do not have access to this workshop.")
        return WorkshopAccessContext(
            user=current_user,
            role=role,
            taller_ids=(workshop_id,),
        )

    raise forbidden_user_error("This endpoint is only available for administrative roles.")
