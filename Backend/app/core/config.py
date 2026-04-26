from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE)


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    registration_token_expire_minutes: int
    lockout_minutes: int
    storage_backend: str
    local_media_root: Path
    triage_ai_provider: str
    triage_ai_api_key: str | None
    triage_ai_model: str
    triage_auto_run_after_report: bool
    triage_min_confidence: int
    triage_ai_timeout_seconds: int
    matchmaking_request_ttl_seconds: int
    workshop_max_action_radius_km: int
    maps_provider: str
    maps_base_url: str
    maps_api_key: str | None
    navigation_arrival_threshold_meters: int
    navigation_provider_timeout_seconds: int
    payment_provider: str
    payment_webhook_token: str | None
    payment_request_expire_minutes: int
    push_provider: str
    fcm_credentials_file: Path | None
    sqlalchemy_echo: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    fcm_credentials_file = os.getenv("FCM_CREDENTIALS_FILE")
    return Settings(
        app_name=os.getenv("APP_NAME", "Proyecto SI2 Backend"),
        environment=os.getenv("APP_ENV", "local"),
        database_url=_get_required_env("DATABASE_URL"),
        jwt_secret_key=_get_required_env("JWT_SECRET_KEY"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        registration_token_expire_minutes=int(
            os.getenv("REGISTRATION_TOKEN_EXPIRE_MINUTES", "15")
        ),
        lockout_minutes=int(os.getenv("LOCKOUT_MINUTES", "5")),
        storage_backend=os.getenv("STORAGE_BACKEND", "local"),
        local_media_root=Path(os.getenv("LOCAL_MEDIA_ROOT", str(BACKEND_DIR / "media"))),
        triage_ai_provider=os.getenv("TRIAGE_AI_PROVIDER", "gemini"),
        triage_ai_api_key=os.getenv("TRIAGE_AI_API_KEY"),
        triage_ai_model=os.getenv("TRIAGE_AI_MODEL", "gemini-2.0-flash"),
        triage_auto_run_after_report=_get_bool_env(
            "TRIAGE_AUTO_RUN_AFTER_REPORT",
            default=False,
        ),
        triage_min_confidence=int(os.getenv("TRIAGE_MIN_CONFIDENCE", "60")),
        triage_ai_timeout_seconds=int(os.getenv("TRIAGE_AI_TIMEOUT_SECONDS", "30")),
        matchmaking_request_ttl_seconds=int(
            os.getenv("MATCHMAKING_REQUEST_TTL_SECONDS", "120")
        ),
        workshop_max_action_radius_km=int(
            os.getenv("WORKSHOP_MAX_ACTION_RADIUS_KM", "100")
        ),
        maps_provider=os.getenv("MAPS_PROVIDER", "osrm"),
        maps_base_url=os.getenv(
            "MAPS_BASE_URL",
            "https://router.project-osrm.org",
        ),
        maps_api_key=os.getenv("MAPS_API_KEY"),
        navigation_arrival_threshold_meters=int(
            os.getenv("NAVIGATION_ARRIVAL_THRESHOLD_METERS", "50")
        ),
        navigation_provider_timeout_seconds=int(
            os.getenv("NAVIGATION_PROVIDER_TIMEOUT_SECONDS", "15")
        ),
        payment_provider=os.getenv("PAYMENT_PROVIDER", "sandbox"),
        payment_webhook_token=os.getenv("PAYMENT_WEBHOOK_TOKEN"),
        payment_request_expire_minutes=int(
            os.getenv("PAYMENT_REQUEST_EXPIRE_MINUTES", "15")
        ),
        push_provider=os.getenv("PUSH_PROVIDER", "sandbox"),
        fcm_credentials_file=(
            Path(fcm_credentials_file)
            if fcm_credentials_file and Path(fcm_credentials_file).is_absolute()
            else (BACKEND_DIR / fcm_credentials_file if fcm_credentials_file else None)
        ),
        sqlalchemy_echo=_get_bool_env("SQLALCHEMY_ECHO", default=False),
    )


settings = get_settings()
