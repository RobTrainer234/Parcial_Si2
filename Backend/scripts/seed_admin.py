from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Administrador, Especialidad, Persona, Taller, TallerEspecialidad, Usuario
from app.packages.seguridad_usuarios.security import hash_password


DEMO_EMAIL = "admin@taller.com"
DEMO_PASSWORD = "Admin123!"
DEMO_CI = "ADMIN-DEMO-001"
DEMO_WORKSHOP_NAME = "Taller Demo SI2"
LOCAL_ENVIRONMENTS = {"local", "dev", "development"}
SPECIALTY_NAMES = [
    "Mecánica",
    "Electricidad",
    "Aire acondicionado",
    "Llantas",
]


def _ensure_local_environment() -> None:
    settings = get_settings()
    environment = settings.environment.strip().lower()
    if environment not in LOCAL_ENVIRONMENTS:
        raise RuntimeError(
            f"seed_admin.py is restricted to local environments. Current APP_ENV={settings.environment!r}."
        )


def _get_user_by_email(db: Session, email: str) -> Usuario | None:
    normalized_email = email.strip().lower()
    return db.scalar(
        select(Usuario).where(func.lower(Usuario.email) == normalized_email)
    )


def _get_persona_by_ci(db: Session, ci: str) -> Persona | None:
    return db.scalar(select(Persona).where(Persona.ci == ci))


def _get_workshop_by_name(db: Session, name: str) -> Taller | None:
    normalized_name = name.strip().lower()
    return db.scalar(
        select(Taller).where(func.lower(Taller.nombre_comercial) == normalized_name)
    )


def _get_or_create_persona(db: Session) -> Persona:
    existing_user = _get_user_by_email(db, DEMO_EMAIL)
    existing_persona = _get_persona_by_ci(db, DEMO_CI)

    if (
        existing_user is not None
        and existing_persona is not None
        and existing_user.id_persona != existing_persona.id_persona
    ):
        raise RuntimeError(
            "Cannot safely seed local admin: email and CI already belong to different personas."
        )

    persona = existing_user.persona if existing_user is not None else existing_persona
    if persona is None:
        persona = Persona(
            nombre="Admin",
            apellido="Taller",
            ci=DEMO_CI,
            telefono="70000001",
            direccion="Demo local",
        )
        db.add(persona)
        db.flush()
        return persona

    persona.nombre = "Admin"
    persona.apellido = "Taller"
    persona.ci = DEMO_CI
    persona.telefono = "70000001"
    persona.direccion = "Demo local"
    db.flush()
    return persona


def _get_or_create_workshop(db: Session) -> Taller:
    workshop = _get_workshop_by_name(db, DEMO_WORKSHOP_NAME)
    if workshop is None:
        workshop = Taller(
            nombre_comercial=DEMO_WORKSHOP_NAME,
            descripcion="Taller demo para pruebas locales del panel administrador.",
            latitud=Decimal("-17.78330000"),
            longitud=Decimal("-63.18210000"),
            radio_accion_km=Decimal("20.00"),
            activo=True,
            acepta_seguro_propio=True,
        )
        db.add(workshop)
        db.flush()
        return workshop

    workshop.nombre_comercial = DEMO_WORKSHOP_NAME
    workshop.descripcion = "Taller demo para pruebas locales del panel administrador."
    workshop.latitud = Decimal("-17.78330000")
    workshop.longitud = Decimal("-63.18210000")
    workshop.radio_accion_km = Decimal("20.00")
    workshop.activo = True
    workshop.acepta_seguro_propio = True
    db.flush()
    return workshop


def _get_or_create_user(db: Session, persona: Persona) -> Usuario:
    user = _get_user_by_email(db, DEMO_EMAIL)

    if user is not None and user.id_persona != persona.id_persona:
        raise RuntimeError(
            "Cannot safely seed local admin: demo email already belongs to a different persona."
        )

    if user is None:
        user = db.scalar(select(Usuario).where(Usuario.id_persona == persona.id_persona))

    if user is None:
        user = Usuario(
            id_persona=persona.id_persona,
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            tipo_usuario="ADMINISTRADOR",
            activo=True,
            intentos=0,
            bloqueado=False,
        )
        db.add(user)
        db.flush()
        return user

    user.email = DEMO_EMAIL
    user.password_hash = hash_password(DEMO_PASSWORD)
    user.tipo_usuario = "ADMINISTRADOR"
    user.activo = True
    user.intentos = 0
    user.bloqueado = False
    user.bloqueado_hasta = None
    db.flush()
    return user


def _get_or_create_admin_relation(db: Session, persona: Persona, workshop: Taller) -> Administrador:
    admin_relation = db.scalar(
        select(Administrador).where(Administrador.id_persona == persona.id_persona)
    )

    if admin_relation is None:
        admin_relation = Administrador(
            id_persona=persona.id_persona,
            id_taller=workshop.id_taller,
            activo=True,
        )
        db.add(admin_relation)
        db.flush()
        return admin_relation

    admin_relation.id_taller = workshop.id_taller
    admin_relation.activo = True
    db.flush()
    return admin_relation


def _get_or_create_specialty(db: Session, name: str) -> Especialidad:
    specialty = db.scalar(
        select(Especialidad).where(func.lower(Especialidad.nombre) == name.strip().lower())
    )
    if specialty is None:
        specialty = Especialidad(nombre=name.strip(), descripcion=None)
        db.add(specialty)
        db.flush()
        return specialty

    specialty.nombre = name.strip()
    db.flush()
    return specialty


def _ensure_workshop_specialties(db: Session, workshop: Taller) -> None:
    for specialty_name in SPECIALTY_NAMES:
        specialty = _get_or_create_specialty(db, specialty_name)
        relation = db.scalar(
            select(TallerEspecialidad).where(
                TallerEspecialidad.id_taller == workshop.id_taller,
                TallerEspecialidad.id_especialidad == specialty.id_especialidad,
            )
        )
        if relation is None:
            db.add(
                TallerEspecialidad(
                    id_taller=workshop.id_taller,
                    id_especialidad=specialty.id_especialidad,
                    activo=True,
                )
            )
        else:
            relation.activo = True


def seed_local_admin() -> None:
    _ensure_local_environment()

    db = SessionLocal()
    try:
        persona = _get_or_create_persona(db)
        _get_or_create_user(db, persona)
        workshop = _get_or_create_workshop(db)
        _get_or_create_admin_relation(db, persona, workshop)
        _ensure_workshop_specialties(db, workshop)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("Local admin seed ready.")
    print(f"Email: {DEMO_EMAIL}")
    print(f"Password: {DEMO_PASSWORD}")
    print(f"Workshop: {DEMO_WORKSHOP_NAME}")


if __name__ == "__main__":
    seed_local_admin()
