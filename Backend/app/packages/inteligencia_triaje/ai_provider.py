from __future__ import annotations

import base64
import json
import re
import socket
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib import error, request

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from app.core.config import get_settings


GROQ_CHAT_COMPLETIONS_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MAX_PROVIDER_RESPONSE_EXCERPT_CHARS = 1000
MAX_PROVIDER_IMAGES = 5
VISION_MODEL_MARKERS = (
    "llama-4",
    "vision",
    "scout",
    "maverick",
)


class TriageProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        http_status_code: int | None = None,
        provider_response_excerpt: str | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        image_count: int | None = None,
        audio_included: bool | None = None,
        audio_omitted_reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status_code = http_status_code
        self.provider_response_excerpt = provider_response_excerpt
        self.provider_name = provider_name
        self.model_name = model_name
        self.image_count = image_count
        self.audio_included = audio_included
        self.audio_omitted_reason = audio_omitted_reason


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
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    summary: str = Field(
        min_length=1,
        validation_alias=AliasChoices("summary", "resumen"),
    )
    severity: str = Field(validation_alias=AliasChoices("severity", "severidad"))
    detected_specialty: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "detected_specialty",
            "especialidad_detectada_nombre",
        ),
    )
    confidence: Decimal = Field(
        ge=0,
        le=100,
        validation_alias=AliasChoices("confidence", "confianza"),
    )
    specific_diagnosis: str | None = None
    suggested_service: str | None = None
    customer_recommendation: str | None = None
    operator_notes: str | None = None
    audio_transcript: str | None = Field(
        default=None,
        validation_alias=AliasChoices("audio_transcript", "transcripcion_audio"),
    )
    audio_summary: str | None = Field(
        default=None,
        validation_alias=AliasChoices("audio_summary", "resumen_audio"),
    )
    audio_analysis_type: str = "NO_AUDIO"
    visual_evidence_tags: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("visual_evidence_tags", "etiquetas_imagen"),
    )
    suggested_tools: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("suggested_tools", "herramientas_sugeridas"),
    )
    requires_tow: bool = Field(
        default=False,
        validation_alias=AliasChoices("requires_tow", "requiere_grua"),
    )
    observations: str | None = Field(
        default=None,
        validation_alias=AliasChoices("observations", "observaciones"),
    )
    requires_manual_review: bool | None = None

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"BAJA", "MEDIA", "ALTA", "CRITICA"}
        if normalized not in allowed:
            raise ValueError("Invalid severity.")
        return normalized

    @field_validator("detected_specialty")
    @classmethod
    def normalize_specialty_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split()).upper()
        return normalized or None

    @field_validator("suggested_tools")
    @classmethod
    def normalize_tools(cls, value: list[str]) -> list[str]:
        return [" ".join(item.split()) for item in value if " ".join(item.split())]

    @field_validator(
        "summary",
        "specific_diagnosis",
        "suggested_service",
        "customer_recommendation",
        "operator_notes",
        "audio_transcript",
        "audio_summary",
        "observations",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @field_validator("audio_transcript")
    @classmethod
    def enforce_audio_null(cls, value: str | None) -> str | None:
        if value is not None:
            raise ValueError("Audio transcription is not supported in Groq triage.")
        return value

    @field_validator("audio_analysis_type")
    @classmethod
    def normalize_audio_analysis_type(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {
            "NO_AUDIO",
            "SPEECH_TRANSCRIPTION",
            "MECHANICAL_SOUND_EXPERIMENTAL",
        }
        if normalized not in allowed:
            raise ValueError("Invalid audio_analysis_type.")
        return normalized

    @field_validator("visual_evidence_tags", mode="before")
    @classmethod
    def normalize_visual_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            normalized = " ".join(value.split())
            return [normalized] if normalized else []
        if isinstance(value, dict):
            tags = [
                " ".join(str(key).split())
                for key, item in value.items()
                if " ".join(str(key).split()) and item not in (None, False, "", 0)
            ]
            return tags
        if isinstance(value, list):
            return [
                " ".join(str(item).split())
                for item in value
                if " ".join(str(item).split())
            ]
        raise ValueError("visual_evidence_tags must be a list, object or null.")

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence_scale(cls, value: Any) -> Decimal:
        try:
            confidence = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("Confidence must be numeric.") from exc

        if confidence < Decimal("0"):
            raise ValueError("Confidence must be between 0 and 100.")
        if confidence == Decimal("0"):
            return confidence
        if confidence <= Decimal("1"):
            confidence *= Decimal("100")
        if confidence > Decimal("100"):
            raise ValueError("Confidence must be between 0 and 100.")
        return confidence


def _build_triage_prompt(
    *,
    description: str,
    reported_specialty_name: str,
    specialty_names: list[str],
    image_count: int,
    audio_transcript: str | None,
    audio_analysis_type: str,
    audio_warning: str | None,
) -> str:
    allowed_specialties = ", ".join(specialty_names)
    audio_context = (
        f"Tipo de analisis de audio: {audio_analysis_type}. "
        f"Transcripcion o nota de audio: {audio_transcript or 'Sin audio o sin transcripcion util.'}. "
    )
    if audio_warning:
        audio_context += f"Advertencia de audio: {audio_warning}. "
    return (
        "Eres un clasificador tecnico preliminar para auxilio vehicular. "
        "Analiza la descripcion del cliente, la transcripcion de audio cuando exista y las imagenes adjuntas. "
        "No inventes hechos que no esten visibles o descritos. "
        "No sobreafirmes ni presentes certezas falsas. "
        "Cuando la evidencia no sea concluyente usa expresiones como posible, probable o se recomienda revisar. "
        "La sospecha inicial reportada por el cliente es: "
        f"{reported_specialty_name}. "
        f"Especialidades permitidas exactamente como catalogo backend: {allowed_specialties}. "
        f"Cantidad de imagenes adjuntas: {image_count}. "
        f"Descripcion del cliente: {description}. "
        f"{audio_context}"
        "Reglas visuales: si una imagen muestra claramente una llanta baja, pinchada, rueda danada o neumatico sin aire, "
        "prefiere detected_specialty=\"Llantas\" cuando exista en el catalogo. "
        "Si muestra bateria, bornes, capot abierto o bahia de motor y la descripcion menciona que no prende, no avanza o se apago, "
        "prefiere detected_specialty=\"BATERIA\" o \"Electricidad\" segun la evidencia disponible. "
        "Si muestra choque, vehiculo inmovil, remolque o dano que impide circular, usa \"GRUA\" o \"MECANICA_GENERAL\" segun severidad y catalogo. "
        "Si la imagen no es clara, no es relevante o no permite identificar la falla, DIAGNOSTICO_GENERAL es aceptable y requiere revision manual. "
        "Incluye etiquetas visuales normalizadas y utiles como flat_tire, tire, wheel, battery, engine_bay, hood_open, tow, crash o immobile cuando apliquen. "
        "Debes devolver SOLO un objeto JSON valido, sin markdown y sin texto adicional. "
        "detected_specialty debe ser exactamente uno de los nombres permitidos o null. "
        "No devuelvas una especialidad fuera del catalogo permitido. "
        "confidence debe ser un numero entre 0 y 100, no entre 0 y 1. "
        "Ejemplo: usa 90 para 90%, no 0.90. "
        "Si el audio contiene voz clara, usa esa explicacion para complementar el analisis. "
        "Si el audio es no verbal, mecanico o sin voz clara, no presentes el resultado como concluyente. "
        "Cuando el audio sea no verbal o no haya transcripcion util, usa audio_analysis_type=\"MECHANICAL_SOUND_EXPERIMENTAL\" y baja la confianza. "
        "visual_evidence_tags debe ser un arreglo corto de etiquetas legibles. "
        "Si la descripcion o las imagenes son ambiguas, elige DIAGNOSTICO_GENERAL o MECANICA_GENERAL cuando exista en el catalogo y marca requires_manual_review=true. "
        "Si el audio es la unica evidencia y no aporta voz clara, marca requires_manual_review=true. "
        "Si no estas seguro, conserva una especialidad permitida amplia, baja la confianza y explica la incertidumbre en summary u observations. "
        "Estructura JSON obligatoria: "
        '{"summary": string, "severity": "BAJA" | "MEDIA" | "ALTA", '
        '"detected_specialty": string | null, "confidence": number, '
        '"specific_diagnosis": string | null, "suggested_service": string | null, '
        '"customer_recommendation": string | null, "operator_notes": string | null, '
        '"audio_transcript": null, "audio_summary": string | null, '
        '"audio_analysis_type": "SPEECH_TRANSCRIPTION" | "MECHANICAL_SOUND_EXPERIMENTAL" | "NO_AUDIO", '
        '"visual_evidence_tags": array de strings, '
        '"suggested_tools": array de strings, "requires_tow": boolean, '
        '"observations": string | null, "requires_manual_review": boolean}.'
    )


def _model_supports_vision(*, provider_name: str, model_name: str) -> bool:
    if provider_name != "groq":
        return False
    normalized_model = model_name.strip().lower()
    return any(marker in normalized_model for marker in VISION_MODEL_MARKERS)


def _sanitize_provider_error_text(value: str | None) -> str | None:
    if not value:
        return None
    sanitized = re.sub(
        r"Authorization:\s*Bearer\s+[A-Za-z0-9._\-]+",
        "Authorization: Bearer [REDACTED]",
        value,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"Bearer\s+[A-Za-z0-9._\-]+",
        "Bearer [REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(r"key=[^&\s]+", "key=[REDACTED]", sanitized, flags=re.IGNORECASE)
    sanitized = sanitized.replace("\r", " ").replace("\n", " ")
    sanitized = " ".join(sanitized.split())
    return sanitized[:MAX_PROVIDER_RESPONSE_EXCERPT_CHARS]


def _build_groq_content_items(
    *,
    prompt: str,
    images: list[AIMediaInput],
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images[:MAX_PROVIDER_IMAGES]:
        data_url = (
            f"data:{image.mime_type};base64,"
            f"{base64.b64encode(image.content_bytes).decode('ascii')}"
        )
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url,
                },
            }
        )
    return content


def _strip_json_fences(value: str) -> str:
    stripped = value.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if not lines:
        return stripped
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_text_from_provider_response(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise TriageProviderInvalidResponseError("Provider returned no choices.")

    first_choice = choices[0]
    message = first_choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return _strip_json_fences(content)

    raise TriageProviderInvalidResponseError("Provider returned no JSON content.")


def _call_groq_chat_completion(
    *,
    provider_name: str,
    model: str,
    api_key: str,
    timeout_seconds: int,
    prompt: str,
    images: list[AIMediaInput],
) -> dict[str, Any]:
    request_body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": _build_groq_content_items(prompt=prompt, images=images),
            }
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    payload_bytes = json.dumps(request_body).encode("utf-8")
    http_request = request.Request(
        GROQ_CHAT_COMPLETIONS_ENDPOINT,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "SI2-AuxilioVial/1.0 (+https://localhost)",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="ignore")
        sanitized_response = _sanitize_provider_error_text(response_text)
        raise TriageProviderError(
            f"Groq request failed with HTTP {exc.code}: {sanitized_response or 'No response body.'}",
            http_status_code=exc.code,
            provider_response_excerpt=sanitized_response,
            provider_name=provider_name,
            model_name=model,
            image_count=min(len(images), MAX_PROVIDER_IMAGES),
            audio_included=False,
        ) from exc
    except socket.timeout as exc:
        raise TriageProviderError(
            "Groq request timed out.",
            provider_name=provider_name,
            model_name=model,
            image_count=min(len(images), MAX_PROVIDER_IMAGES),
            audio_included=False,
        ) from exc
    except error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if reason:
            raise TriageProviderError(
                f"Groq request failed: {reason}",
                provider_name=provider_name,
                model_name=model,
                image_count=min(len(images), MAX_PROVIDER_IMAGES),
                audio_included=False,
            ) from exc
        raise TriageProviderError(
            "Groq request failed.",
            provider_name=provider_name,
            model_name=model,
            image_count=min(len(images), MAX_PROVIDER_IMAGES),
            audio_included=False,
        ) from exc


def _get_triage_provider_settings() -> tuple[str, str, str]:
    settings = get_settings()
    provider_name = (settings.triage_ai_provider or "").strip().lower()
    if not provider_name:
        raise TriageProviderNotConfiguredError("Missing TRIAGE_AI_PROVIDER setting.")
    if provider_name != "groq":
        raise TriageProviderNotConfiguredError(
            f"Unsupported TRIAGE_AI_PROVIDER setting: {settings.triage_ai_provider!r}."
        )

    model_name = (settings.triage_ai_model or "").strip()
    if not model_name:
        raise TriageProviderNotConfiguredError("Missing TRIAGE_AI_MODEL setting.")

    api_key = (settings.triage_ai_api_key or "").strip()
    if not api_key:
        raise TriageProviderNotConfiguredError("Missing TRIAGE_AI_API_KEY setting.")

    return provider_name, model_name, api_key


def run_multimodal_triage(
    *,
    description: str,
    reported_specialty_name: str,
    specialty_names: list[str],
    images: list[AIMediaInput],
    audio: AIMediaInput | None,
    audio_transcript: str | None,
    audio_analysis_type: str,
    audio_warning: str | None = None,
) -> tuple[NormalizedTriageAIResult, dict[str, Any]]:
    settings = get_settings()
    provider_name, model_name, api_key = _get_triage_provider_settings()
    image_mime_types = [image.mime_type for image in images]
    image_bytes_total = sum(len(image.content_bytes) for image in images)
    vision_enabled = _model_supports_vision(
        provider_name=provider_name,
        model_name=model_name,
    )
    images_for_provider = images[:MAX_PROVIDER_IMAGES] if vision_enabled else []

    prompt = _build_triage_prompt(
        description=description,
        reported_specialty_name=reported_specialty_name,
        specialty_names=specialty_names,
        image_count=len(images_for_provider),
        audio_transcript=audio_transcript,
        audio_analysis_type=audio_analysis_type,
        audio_warning=audio_warning,
    )

    provider_metadata: dict[str, Any] = {
        "provider": provider_name,
        "model": model_name,
        "vision_enabled": vision_enabled,
        "audio_included": bool(audio_transcript or audio_warning),
        "image_count": len(images_for_provider),
        "image_count_received_by_backend": len(images),
        "image_count_sent_to_ai": len(images_for_provider),
        "image_mime_types": image_mime_types,
        "image_bytes_total": image_bytes_total,
        "used_image_evidence": bool(images_for_provider),
    }
    if images and not images_for_provider:
        provider_metadata["image_omitted_reason"] = "triage_model_without_vision_support"
    if audio is not None:
        provider_metadata["audio_analysis_type"] = audio_analysis_type
        provider_metadata["audio_warning"] = audio_warning
        provider_metadata["audio_transcript_available"] = bool(audio_transcript)
        if not audio_transcript and audio_warning:
            provider_metadata["audio_omitted_reason"] = "no_useful_audio_transcription"

    provider_response = _call_groq_chat_completion(
        provider_name=provider_name,
        model=model_name,
        api_key=api_key,
        timeout_seconds=settings.triage_ai_timeout_seconds,
        prompt=prompt,
        images=images_for_provider,
    )

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
    provider_metadata["raw_detected_specialty"] = raw_json.get("detected_specialty")
    return normalized, provider_metadata
