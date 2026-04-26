from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings


PASSWORD_ALGORITHM = "sha256"
PASSWORD_ITERATIONS = 390_000
PASSWORD_SALT_BYTES = 16
settings = get_settings()


def utc_now() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        PASSWORD_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii")
    key_b64 = base64.urlsafe_b64encode(derived_key).decode("ascii")
    return f"pbkdf2_{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt_b64}${key_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations_raw, salt_b64, key_b64 = password_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if not scheme.startswith("pbkdf2_"):
        return False

    algorithm = scheme.removeprefix("pbkdf2_")
    try:
        iterations = int(iterations_raw)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected_key = base64.urlsafe_b64decode(key_b64.encode("ascii"))
    except (ValueError, TypeError):
        return False

    derived_key = hashlib.pbkdf2_hmac(algorithm, password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(derived_key, expected_key)


def create_access_token(*, user_id: int, role: str, home_hint: str) -> str:
    expires_at = utc_now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "home_hint": home_hint,
        "type": "access",
        "iat": int(utc_now().timestamp()),
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_registration_token(
    *,
    pending_registration_id: int,
    flow: str,
    expires_at: datetime,
) -> str:
    token_payload = {
        "type": "registration",
        "pending_registration_id": pending_registration_id,
        "flow": flow,
        "iat": int(utc_now().timestamp()),
        "exp": expires_at,
    }
    return jwt.encode(token_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type.")
    return payload


def generate_verification_code(length: int = 6) -> str:
    upper_bound = 10**length
    return f"{secrets.randbelow(upper_bound):0{length}d}"


def build_verification_code_digest(code: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
