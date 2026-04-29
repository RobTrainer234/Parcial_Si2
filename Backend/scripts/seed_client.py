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
from app.models import Cliente, Persona, Usuario
from app.packages.seguridad_usuarios.security import hash_password

DEMO_EMAIL = "cliente@email.com"
DEMO_PASSWORD = "password123"
DEMO_CI = "CLIENTE-DEMO-001"
LOCAL_ENVIRONMENTS = {"local", "dev", "development"}

def _ensure_local_environment() -> None:
    settings = get_settings()
    environment = settings.environment.strip().lower()
    if environment not in LOCAL_ENVIRONMENTS:
        raise RuntimeError(
            f"seed_client.py is restricted to local environments. Current APP_ENV={settings.environment!r}."
        )

def _get_user_by_email(db: Session, email: str) -> Usuario | None:
    normalized_email = email.strip().lower()
    return db.scalar(
        select(Usuario).where(func.lower(Usuario.email) == normalized_email)
    )

def _get_persona_by_ci(db: Session, ci: str) -> Persona | None:
    return db.scalar(select(Persona).where(Persona.ci == ci))

def _get_or_create_persona(db: Session) -> Persona:
    existing_user = _get_user_by_email(db, DEMO_EMAIL)
    existing_persona = _get_persona_by_ci(db, DEMO_CI)

    if (
        existing_user is not None
        and existing_persona is not None
        and existing_user.id_persona != existing_persona.id_persona
    ):
        raise RuntimeError(
            "Cannot safely seed local client: email and CI already belong to different personas."
        )

    persona = existing_user.persona if existing_user is not None else existing_persona
    if persona is None:
        persona = Persona(
            nombre="Cliente",
            apellido="Demo",
            ci=DEMO_CI,
            telefono="70000002",
            direccion="Demo local",
        )
        db.add(persona)
        db.flush()
        return persona

    persona.nombre = "Cliente"
    persona.apellido = "Demo"
    persona.ci = DEMO_CI
    persona.telefono = "70000002"
    persona.direccion = "Demo local"
    db.flush()
    return persona

def _get_or_create_user(db: Session, persona: Persona) -> Usuario:
    user = _get_user_by_email(db, DEMO_EMAIL)

    if user is not None and user.id_persona != persona.id_persona:
        raise RuntimeError(
            "Cannot safely seed local client: demo email already belongs to a different persona."
        )

    if user is None:
        user = db.scalar(select(Usuario).where(Usuario.id_persona == persona.id_persona))

    if user is None:
        user = Usuario(
            id_persona=persona.id_persona,
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            tipo_usuario="CLIENTE",
            activo=True,
            intentos=0,
            bloqueado=False,
        )
        db.add(user)
        db.flush()
        return user

    user.email = DEMO_EMAIL
    user.password_hash = hash_password(DEMO_PASSWORD)
    user.tipo_usuario = "CLIENTE"
    user.activo = True
    user.intentos = 0
    user.bloqueado = False
    user.bloqueado_hasta = None
    db.flush()
    return user

def _get_or_create_client_relation(db: Session, persona: Persona) -> Cliente:
    client_relation = db.scalar(
        select(Cliente).where(Cliente.id_persona == persona.id_persona)
    )

    if client_relation is None:
        client_relation = Cliente(
            id_persona=persona.id_persona,
        )
        db.add(client_relation)
        db.flush()
        return client_relation

    db.flush()
    return client_relation

def seed_local_client() -> None:
    _ensure_local_environment()

    db = SessionLocal()
    try:
        persona = _get_or_create_persona(db)
        _get_or_create_user(db, persona)
        _get_or_create_client_relation(db, persona)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("Local client seed ready.")
    print(f"Email: {DEMO_EMAIL}")
    print(f"Password: {DEMO_PASSWORD}")

if __name__ == "__main__":
    seed_local_client()
