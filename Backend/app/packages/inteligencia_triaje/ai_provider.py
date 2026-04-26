from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib import error, parse, request

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.config import get_settings


class TriageProviderError(Exception):
    pass


class TriageProviderNotConfiguredError(TriageProviderError):
    pass


class TriageProviderInvalidResponseError(TriageProviderError):
    pass


@dataclass(frozen=True)
class AIMediaInput:
    content_bytes: bytes
    mime_type: str
    locator: str


class NormalizedTriageAIResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    resumen: str = Field(min_length=1)
    severidad: str
    especialidad_detectada_nombre: str | None = None
    confianza: Decimal = Field(ge=0, le=100)
    transcripcion_audio: str | None = None
    etiquetas_imagen: list[str] | dict[str, Any] | None = None
    herramientas_sugeridas: list[str] = Field(default_factory=list)
    requiere_grua: bool = False
    observaciones: str | None = None

    @field_validator("severidad")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"BAJA", "MEDIA", "ALTA", "CRITICA"}
        if normalized not in allowed:
            raise ValueError("Invalid severity.")
        return normalized

    @field_validator("especialidad_detectada_nombre")
    @classmethod
    def normalize_specialty_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split()).upper()
        return normalized or None

    @field_validator("herramientas_sugeridas")
    @classmethod
    def normalize_tools(cls, value: list[str]) -> list[str]:
        return [" ".join(item.split()) for item in value if " ".join(item.split())]

    @field_validator("transcripcion_audio", "observaciones")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None


def _triage_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "resumen",
            "severidad",
            "especialidad_detectada_nombre",
            "confianza",
            "transcripcion_audio",
            "etiquetas_imagen",
            "herramientas_sugeridas",
            "requiere_grua",
            "observaciones",
        ],
        "properties": {
            "resumen": {
                "type": "string",
                "description": "Resumen tecnico preliminar del incidente.",
            },
            "severidad": {
                "type": "string",
                "enum": ["BAJA", "MEDIA", "ALTA", "CRITICA"],
            },
            "especialidad_detectada_nombre": {
                "type": ["string", "null"],
                "description": "Uno de los nombres de especialidad permitidos o null si no hay certeza.",
            },
            "confianza": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },
            "transcripcion_audio": {
                "type": ["string", "null"],
            },
            "etiquetas_imagen": {
                "type": ["array", "object", "null"],
                "items": {"type": "string"},
            },
            "herramientas_sugeridas": {
                "type": "array",
                "items": {"type": "string"},
            },
            "requiere_grua": {"type": "boolean"},
            "observaciones": {"type": ["string", "null"]},
        },
    }


def _build_triage_prompt(
    *,
    description: str,
    reported_specialty_name: str,
    specialty_names: list[str],
    has_audio: bool,
    image_count: int,
) -> str:
    return (
        "Eres un clasificador tecnico preliminar para auxilio vehicular. "
        "Analiza descripcion, audio e imagenes si existen y responde SOLO JSON valido. "
        "No inventes datos no observables. "
        "La especialidad detectada debe ser exactamente uno de estos nombres o null: "
        f"{', '.join(specialty_names)}. "
        "Si no hay suficiente certeza, usa confianza baja y especialidad_detectada_nombre null. "
        f"El cliente reporto inicialmente la especialidad {reported_specialty_name}. "
        f"Hay audio: {'si' if has_audio else 'no'}. "
        f"Cantidad de imagenes: {image_count}. "
        f"Descripcion del cliente: {description}"
    )


def _extract_text_from_provider_response(response_payload: dict[str, Any]) -> str:
    candidates = response_payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise TriageProviderInvalidResponseError("Provider returned no candidates.")

    first_candidate = candidates[0]
    content = first_candidate.get("content") or {}
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise TriageProviderInvalidResponseError("Provider returned no text parts.")

    for part in parts:
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            return text

    raise TriageProviderInvalidResponseError("Provider returned no JSON text.")


def _call_gemini_generate_content(
    *,
    model: str,
    api_key: str,
    timeout_seconds: int,
    prompt: str,
    images: list[AIMediaInput],
    audio: AIMediaInput | None,
) -> dict[str, Any]:
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{parse.quote(model)}:generateContent?key={parse.quote(api_key)}"
    )
    parts: list[dict[str, Any]] = [{"text": prompt}]
    for image in images:
        parts.append(
            {
                "inline_data": {
                    "mime_type": image.mime_type,
                    "data": base64.b64encode(image.content_bytes).decode("ascii"),
                }
            }
        )
    if audio is not None:
        parts.append(
            {
                "inline_data": {
                    "mime_type": audio.mime_type,
                    "data": base64.b64encode(audio.content_bytes).decode("ascii"),
                }
            }
        )

    request_body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": _triage_response_schema(),
            "temperature": 0.2,
        },
    }
    payload_bytes = json.dumps(request_body).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=payload_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="ignore")
        raise TriageProviderError(
            f"Gemini request failed with HTTP {exc.code}: {response_text}"
        ) from exc
    except error.URLError as exc:
        raise TriageProviderError("Gemini request failed.") from exc


def run_multimodal_triage(
    *,
    description: str,
    reported_specialty_name: str,
    specialty_names: list[str],
    images: list[AIMediaInput],
    audio: AIMediaInput | None,
) -> tuple[NormalizedTriageAIResult, dict[str, Any]]:
    settings = get_settings()
    if settings.triage_ai_provider.lower() != "gemini":
        raise TriageProviderNotConfiguredError("Configured triage AI provider is not supported.")
    if not settings.triage_ai_api_key:
        raise TriageProviderNotConfiguredError("Triage AI provider is not configured.")

    prompt = _build_triage_prompt(
        description=description,
        reported_specialty_name=reported_specialty_name,
        specialty_names=specialty_names,
        has_audio=audio is not None,
        image_count=len(images),
    )

    provider_metadata: dict[str, Any] = {
        "provider": settings.triage_ai_provider,
        "model": settings.triage_ai_model,
        "audio_included": audio is not None,
        "image_count": len(images),
    }

    try:
        provider_response = _call_gemini_generate_content(
            model=settings.triage_ai_model,
            api_key=settings.triage_ai_api_key,
            timeout_seconds=settings.triage_ai_timeout_seconds,
            prompt=prompt,
            images=images,
            audio=audio,
        )
    except TriageProviderError:
        if audio is not None:
            provider_response = _call_gemini_generate_content(
                model=settings.triage_ai_model,
                api_key=settings.triage_ai_api_key,
                timeout_seconds=settings.triage_ai_timeout_seconds,
                prompt=prompt,
                images=images,
                audio=None,
            )
            provider_metadata["audio_included"] = False
            provider_metadata["audio_omitted_reason"] = "provider_retry_without_audio"
        else:
            raise

    response_text = _extract_text_from_provider_response(provider_response)
    try:
        raw_json = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise TriageProviderInvalidResponseError("Provider returned invalid JSON.") from exc

    try:
        normalized = NormalizedTriageAIResult.model_validate(raw_json)
    except ValidationError as exc:
        raise TriageProviderInvalidResponseError("Provider returned invalid triage schema.") from exc

    provider_metadata["raw_response"] = raw_json
    return normalized, provider_metadata
