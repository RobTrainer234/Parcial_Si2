from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.incidente import Incidente
from app.packages.inteligencia_triaje.ai_provider import (
    MAX_PROVIDER_IMAGES,
    NormalizedTriageAIResult,
    TriageProviderError,
    TriageProviderInvalidResponseError,
    TriageProviderNotConfiguredError,
    _call_groq_chat_completion,
    _extract_text_from_provider_response,
    _get_triage_provider_settings,
)
from app.packages.inteligencia_triaje.service import (
    _get_specialty_catalog,
    _load_incident_media_inputs,
    run_multimodal_triage,
)


def _print_settings() -> None:
    settings = get_settings()
    print(f"provider={settings.triage_ai_provider!r}")
    print(f"model={settings.triage_ai_model!r}")
    print(f"key_present={bool(settings.triage_ai_api_key)}")
    print(f"key_len={len(settings.triage_ai_api_key or '')}")


def _print_provider_error(prefix: str, exc: Exception) -> None:
    print(f"{prefix}_error_class={exc.__class__.__name__}")
    if isinstance(exc, TriageProviderError):
        print(f"{prefix}_http_status={exc.http_status_code!r}")
        print(f"{prefix}_provider={exc.provider_name!r}")
        print(f"{prefix}_model={exc.model_name!r}")
        print(f"{prefix}_image_count={exc.image_count!r}")
        print(f"{prefix}_audio_included={exc.audio_included!r}")
        print(f"{prefix}_audio_omitted_reason={exc.audio_omitted_reason!r}")
        print(f"{prefix}_provider_response={exc.provider_response_excerpt!r}")
    print(f"{prefix}_message={str(exc)!r}")


def _debug_text_only() -> bool:
    settings = get_settings()
    provider_name, model_name, api_key = _get_triage_provider_settings()
    prompt = (
        'Return JSON exactly: {"resumen":"ok","severidad":"BAJA",'
        '"especialidad_detectada_nombre":null,"confianza":80,'
        '"transcripcion_audio":null,"etiquetas_imagen":null,'
        '"herramientas_sugeridas":[],"requiere_grua":false,"observaciones":null}'
    )
    try:
        payload = _call_groq_chat_completion(
            provider_name=provider_name,
            model=model_name,
            api_key=api_key,
            timeout_seconds=settings.triage_ai_timeout_seconds,
            prompt=prompt,
            images=[],
        )
        response_text = _extract_text_from_provider_response(payload)
        raw_json = json.loads(response_text)
        normalized = NormalizedTriageAIResult.model_validate(raw_json)
    except (
        TriageProviderNotConfiguredError,
        TriageProviderInvalidResponseError,
        TriageProviderError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        _print_provider_error("text_only", exc)
        return False

    print("text_only_ok=True")
    print("text_only_image_count=0")
    print("text_only_audio_omitted_reason=None")
    print(f"text_only_response_text={response_text[:500]!r}")
    print(f"text_only_validated_summary={normalized.resumen!r}")
    return True


def _debug_incident(incident_id: int) -> bool:
    session = SessionLocal()
    try:
        incident = session.get(Incidente, incident_id)
        if incident is None:
            print(f"incident_{incident_id}_missing=True")
            return False

        images, audio_input = _load_incident_media_inputs(incident)
        specialties, _ = _get_specialty_catalog(session)
        print(f"incident_id={incident.id_incidente}")
        print(f"incident_state={incident.estado!r}")
        print(f"incident_image_count={min(len(images), MAX_PROVIDER_IMAGES)}")
        print(f"incident_audio_present={audio_input is not None}")
        for index, image in enumerate(images[:MAX_PROVIDER_IMAGES], start=1):
            print(
                f"incident_image_{index}_mime={image.mime_type!r} size_bytes={len(image.content_bytes)}"
            )

        normalized, metadata = run_multimodal_triage(
            description=incident.descripcion_cliente,
            reported_specialty_name=incident.especialidad_reportada_cliente.nombre,
            specialty_names=[item.nombre for item in specialties],
            images=images,
            audio=audio_input,
        )
    except (
        TriageProviderNotConfiguredError,
        TriageProviderInvalidResponseError,
        TriageProviderError,
    ) as exc:
        _print_provider_error("incident", exc)
        return False
    finally:
        session.close()

    print("incident_ok=True")
    print(f"incident_provider={metadata.get('provider')!r}")
    print(f"incident_model={metadata.get('model')!r}")
    print(f"incident_audio_omitted_reason={metadata.get('audio_omitted_reason')!r}")
    print(f"incident_validated_summary={normalized.resumen!r}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident-id", type=int)
    args = parser.parse_args()

    _print_settings()

    try:
        provider_name, model_name, _ = _get_triage_provider_settings()
        print(f"configured_provider={provider_name!r}")
        print(f"configured_model={model_name!r}")
    except TriageProviderNotConfiguredError as exc:
        _print_provider_error("settings", exc)
        return 2

    ok = _debug_text_only()
    if args.incident_id is not None:
        ok = _debug_incident(args.incident_id) and ok

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
