from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.config import get_settings
from app.packages.inteligencia_triaje.ai_provider import (
    TriageProviderError,
    TriageProviderNotConfiguredError,
    _call_groq_chat_completion,
    _extract_text_from_provider_response,
)
from app.packages.inteligencia_triaje.audio_provider import (
    AudioProviderError,
    AudioProviderNotConfiguredError,
    AudioTranscriptionInput,
    transcribe_audio,
)

from .schemas import (
    VoiceDashboardFiltersResponse,
    VoiceDashboardIntentResponse,
    VoiceDashboardReportResponse,
    WorkshopDashboardOverviewResponse,
)


class _IntentModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    intent: str
    focus: str | None = None
    metric: str | None = None
    requested_period: str | None = None


class _ReportModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    report_text: str
    data_available: bool
    warnings: list[str] = []


def _get_report_provider_settings() -> tuple[str, str, str]:
    settings = get_settings()
    provider_name = (settings.report_ai_provider or "").strip().lower()
    if not provider_name:
        raise TriageProviderNotConfiguredError("Missing REPORT_AI_PROVIDER setting.")
    if provider_name != "groq":
        raise TriageProviderNotConfiguredError(
            f"Unsupported REPORT_AI_PROVIDER setting: {settings.report_ai_provider!r}."
        )

    model_name = (settings.report_ai_model or "").strip()
    if not model_name:
        raise TriageProviderNotConfiguredError("Missing REPORT_AI_MODEL setting.")

    api_key = (settings.report_ai_api_key or "").strip()
    if not api_key:
        raise TriageProviderNotConfiguredError("Missing REPORT_AI_API_KEY setting.")
    return provider_name, model_name, api_key


def _run_report_json_prompt(prompt: str) -> dict[str, Any]:
    settings = get_settings()
    provider_name, model_name, api_key = _get_report_provider_settings()
    response = _call_groq_chat_completion(
        provider_name=provider_name,
        model=model_name,
        api_key=api_key,
        timeout_seconds=settings.triage_ai_timeout_seconds,
        prompt=prompt,
        images=[],
    )
    return json.loads(_extract_text_from_provider_response(response))


def _interpret_request(transcription: str) -> VoiceDashboardIntentResponse:
    prompt = (
        "Interpreta una solicitud de voz para un dashboard de taller vehicular. "
        "Devuelve solo JSON valido con las claves intent, focus, metric y requested_period. "
        "Intent permitidos: general_overview, pending_payments, top_operator, failure_types, "
        "service_summary, operational_alerts, unknown. "
        "Si la solicitud es ambigua usa unknown. "
        f"Solicitud transcrita: {transcription}"
    )
    try:
        payload = _run_report_json_prompt(prompt)
        interpreted = _IntentModel.model_validate(payload)
    except (TriageProviderError, TriageProviderNotConfiguredError, ValidationError, json.JSONDecodeError):
        interpreted = _IntentModel(intent="unknown")

    return VoiceDashboardIntentResponse(
        intent=interpreted.intent,
        focus=interpreted.focus,
        metric=interpreted.metric,
        requested_period=interpreted.requested_period,
    )


def _fallback_report_text(
    *,
    overview: WorkshopDashboardOverviewResponse,
    interpreted_intent: VoiceDashboardIntentResponse,
) -> tuple[str, bool, list[str]]:
    kpis = overview.kpis
    financial = overview.financial
    top_operario = overview.operarios.operario_ranking[0] if overview.operarios.operario_ranking else None
    top_specialty = (
        overview.operations.incidents_by_detected_specialty[0]
        if overview.operations.incidents_by_detected_specialty
        else None
    )

    if interpreted_intent.intent == "pending_payments":
        return (
            (
                f"Pagos pendientes en el periodo: {financial.pending_payments}. "
                f"Ingresos confirmados: BOB {financial.total_revenue}."
            ),
            True,
            [],
        )
    if interpreted_intent.intent == "top_operator":
        if top_operario is None:
            return ("No hay datos suficientes de operarios para ese periodo.", False, ["insufficient_operator_data"])
        return (
            (
                f"El operario con mejor desempeno es {top_operario.nombre_completo}. "
                f"Servicios completados: {top_operario.completed_services}. "
                f"Calificacion promedio: {top_operario.average_rating or 'sin datos'}."
            ),
            True,
            [],
        )
    if interpreted_intent.intent == "failure_types":
        if top_specialty is None:
            return ("No hay datos suficientes de tipos de falla para ese periodo.", False, ["insufficient_failure_data"])
        return (
            (
                f"La especialidad o tipo de falla mas frecuente es {top_specialty.label} "
                f"con {top_specialty.count} incidente(s) registrados en el periodo."
            ),
            True,
            [],
        )
    if interpreted_intent.intent in {"service_summary", "general_overview", "operational_alerts", "unknown"}:
        return (
            (
                f"Resumen del periodo: {kpis.pending_requests} solicitudes pendientes, "
                f"{kpis.active_services} servicios activos, "
                f"{kpis.completed_services} servicios completados y "
                f"{financial.pending_payments} pagos pendientes."
            ),
            True,
            ([] if interpreted_intent.intent != "unknown" else ["intent_interpreted_as_general_overview"]),
        )

    return ("No hay datos suficientes para generar ese reporte.", False, ["unsupported_report_intent"])


def _generate_grounded_report(
    *,
    overview: WorkshopDashboardOverviewResponse,
    transcription: str,
    interpreted_intent: VoiceDashboardIntentResponse,
) -> tuple[str, bool, list[str]]:
    snapshot = json.dumps(
        {
            "period": overview.period.model_dump(mode="json"),
            "kpis": overview.kpis.model_dump(mode="json"),
            "operations": overview.operations.model_dump(mode="json"),
            "financial": overview.financial.model_dump(mode="json"),
            "operarios": overview.operarios.model_dump(mode="json"),
            "reputation": overview.reputation.model_dump(mode="json"),
            "action_items": [item.model_dump(mode="json") for item in overview.action_items[:8]],
        },
        ensure_ascii=False,
    )
    prompt = (
        "Genera un reporte ejecutivo breve en espanol usando exclusivamente los datos JSON entregados. "
        "No inventes metricas. Si faltan datos dilo explicitamente. "
        "Devuelve solo JSON valido con report_text, data_available y warnings. "
        f"Solicitud de voz transcrita: {transcription}. "
        f"Intencion interpretada: {interpreted_intent.model_dump(mode='json')}. "
        f"Datos reales del backend: {snapshot}"
    )
    try:
        payload = _run_report_json_prompt(prompt)
        report = _ReportModel.model_validate(payload)
        return report.report_text, report.data_available, report.warnings
    except (TriageProviderError, TriageProviderNotConfiguredError, ValidationError, json.JSONDecodeError):
        return _fallback_report_text(
            overview=overview,
            interpreted_intent=interpreted_intent,
        )


def build_dashboard_voice_report(
    *,
    audio_bytes: bytes,
    filename: str,
    mime_type: str,
    overview: WorkshopDashboardOverviewResponse,
    scope: str,
    date_from: datetime | None,
    date_to: datetime | None,
) -> VoiceDashboardReportResponse:
    warnings: list[str] = []
    try:
        transcription = transcribe_audio(
            audio_input=AudioTranscriptionInput(
                content_bytes=audio_bytes,
                filename=filename,
                mime_type=mime_type,
            ),
            prompt="Transcribe una solicitud de reporte de negocio en espanol.",
        )
        transcription_text = transcription.transcript_text
        if transcription.warning:
            warnings.append(transcription.warning)
    except (AudioProviderError, AudioProviderNotConfiguredError):
        transcription_text = None
        warnings.append("audio_transcription_failed")

    if not transcription_text:
        interpreted_intent = VoiceDashboardIntentResponse(intent="unknown")
        generated_report = "No se pudo obtener una transcripcion util del audio. Intenta grabar una solicitud con voz mas clara."
        data_available = False
    else:
        interpreted_intent = _interpret_request(transcription_text)
        generated_report, data_available, report_warnings = _generate_grounded_report(
            overview=overview,
            transcription=transcription_text,
            interpreted_intent=interpreted_intent,
        )
        warnings.extend(report_warnings)

    return VoiceDashboardReportResponse(
        transcription=transcription_text,
        interpreted_intent=interpreted_intent,
        generated_report=generated_report,
        used_filters=VoiceDashboardFiltersResponse(
            scope=scope,
            date_from=date_from,
            date_to=date_to,
        ),
        data_available=data_available,
        warnings=warnings,
    )
