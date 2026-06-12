from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib import error, request
from uuid import uuid4

from app.core.config import get_settings


GROQ_AUDIO_TRANSCRIPTIONS_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
MAX_PROVIDER_RESPONSE_EXCERPT_CHARS = 1000


class AudioProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        http_status_code: int | None = None,
        provider_response_excerpt: str | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status_code = http_status_code
        self.provider_response_excerpt = provider_response_excerpt
        self.provider_name = provider_name
        self.model_name = model_name


class AudioProviderNotConfiguredError(AudioProviderError):
    pass


@dataclass(frozen=True)
class AudioTranscriptionResult:
    transcript_text: str | None
    language: str | None
    duration_seconds: Decimal | None
    provider: str
    model: str
    confidence: Decimal | None
    warning: str | None = None
    raw_response: dict[str, Any] | None = None


@dataclass(frozen=True)
class AudioTranscriptionInput:
    content_bytes: bytes
    filename: str
    mime_type: str

    @classmethod
    def from_path(cls, path: Path, *, mime_type: str) -> "AudioTranscriptionInput":
        return cls(
            content_bytes=path.read_bytes(),
            filename=path.name,
            mime_type=mime_type,
        )


def _sanitize_provider_error_text(value: str | None) -> str | None:
    if not value:
        return None
    sanitized = value.replace("\r", " ").replace("\n", " ")
    sanitized = " ".join(sanitized.split())
    return sanitized[:MAX_PROVIDER_RESPONSE_EXCERPT_CHARS]


def _build_multipart_form_data(
    *,
    fields: dict[str, str],
    file_field_name: str,
    file_value: AudioTranscriptionInput,
) -> tuple[bytes, str]:
    boundary = f"----SI2Boundary{uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{file_field_name}"; '
                f'filename="{file_value.filename}"\r\n'
            ).encode("utf-8"),
            f"Content-Type: {file_value.mime_type}\r\n\r\n".encode("utf-8"),
            file_value.content_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks), boundary


def _get_voice_provider_settings() -> tuple[str, str, str]:
    settings = get_settings()
    provider_name = (settings.voice_ai_provider or "").strip().lower()
    if not provider_name:
        raise AudioProviderNotConfiguredError("Missing VOICE_AI_PROVIDER setting.")
    if provider_name != "groq":
        raise AudioProviderNotConfiguredError(
            f"Unsupported VOICE_AI_PROVIDER setting: {settings.voice_ai_provider!r}."
        )

    model_name = (settings.voice_ai_model or "").strip()
    if not model_name:
        raise AudioProviderNotConfiguredError("Missing VOICE_AI_MODEL setting.")

    api_key = (settings.voice_ai_api_key or "").strip()
    if not api_key:
        raise AudioProviderNotConfiguredError("Missing VOICE_AI_API_KEY setting.")

    return provider_name, model_name, api_key


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def transcribe_audio(
    *,
    audio_input: AudioTranscriptionInput,
    prompt: str | None = None,
    language: str | None = None,
) -> AudioTranscriptionResult:
    settings = get_settings()
    provider_name, model_name, api_key = _get_voice_provider_settings()
    fields = {
        "model": model_name,
        "response_format": "verbose_json",
        "temperature": "0",
    }
    if prompt:
        fields["prompt"] = prompt
    if language:
        fields["language"] = language

    body, boundary = _build_multipart_form_data(
        fields=fields,
        file_field_name="file",
        file_value=audio_input,
    )
    http_request = request.Request(
        GROQ_AUDIO_TRANSCRIPTIONS_ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": "SI2-AuxilioVial/1.0 (+https://localhost)",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=settings.triage_ai_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="ignore")
        raise AudioProviderError(
            f"Groq audio request failed with HTTP {exc.code}.",
            http_status_code=exc.code,
            provider_response_excerpt=_sanitize_provider_error_text(response_text),
            provider_name=provider_name,
            model_name=model_name,
        ) from exc
    except socket.timeout as exc:
        raise AudioProviderError(
            "Groq audio request timed out.",
            provider_name=provider_name,
            model_name=model_name,
        ) from exc
    except error.URLError as exc:
        reason = getattr(exc, "reason", None)
        raise AudioProviderError(
            f"Groq audio request failed: {reason or 'unknown network error'}.",
            provider_name=provider_name,
            model_name=model_name,
        ) from exc

    transcript_text = payload.get("text")
    normalized_text = " ".join(str(transcript_text).split()) if transcript_text else None
    warning = None
    if not normalized_text:
        warning = "Transcripcion vacia o no concluyente."

    return AudioTranscriptionResult(
        transcript_text=normalized_text,
        language=(payload.get("language") or None),
        duration_seconds=_to_decimal(payload.get("duration")),
        provider=provider_name,
        model=model_name,
        confidence=_to_decimal(payload.get("confidence")),
        warning=warning,
        raw_response=payload,
    )
