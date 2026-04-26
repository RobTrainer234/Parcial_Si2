from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

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


def require_workshop_admin_context(
    current_user: Usuario = Depends(get_current_user),
) -> WorkshopAdminContext:
    if current_user.tipo_usuario != "ADMINISTRADOR":
        raise forbidden_user_error("This endpoint is only available for ADMINISTRADOR.")

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
