from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping
import unicodedata


MANUAL_REVIEW_CONFIDENCE_FLOOR = 70
GENERAL_DIAGNOSIS_SPECIALTY = "DIAGNOSTICO GENERAL"


@dataclass(frozen=True)
class TriageFallbackContent:
    specific_diagnosis: str
    suggested_service: str
    customer_recommendation: str
    operator_notes: str


@dataclass(frozen=True)
class TriageDiagnosisDetails:
    detected_specialty: str | None
    raw_detected_specialty: str | None
    mapped_detected_specialty: str | None
    specialty_override_reason: str | None
    severity: str | None
    confidence: Decimal | None
    specific_diagnosis: str | None
    suggested_service: str | None
    customer_recommendation: str | None
    operator_notes: str | None
    visual_evidence_tags: list[str]
    requires_manual_review: bool
    summary: str | None
    manual_review_reasons: list[str]


_FALLBACK_BY_SPECIALTY: dict[str, TriageFallbackContent] = {
    "LLANTAS": TriageFallbackContent(
        specific_diagnosis="Posible llanta desinflada, pinchada o danada.",
        suggested_service="Cambio de llanta, parchado o revision de neumatico.",
        customer_recommendation=(
            "Estaciona en una zona segura y activa luces de emergencia."
        ),
        operator_notes=(
            "Revisar presion, dano visible, valvula y estado de la llanta de repuesto."
        ),
    ),
    "BATERIA": TriageFallbackContent(
        specific_diagnosis="Posible bateria descargada o falla inicial de encendido.",
        suggested_service="Auxilio por bateria o revision electrica basica.",
        customer_recommendation=(
            "Evita intentar encender repetidamente el vehiculo."
        ),
        operator_notes="Revisar voltaje, bornes, alternador y consumo electrico.",
    ),
    "ELECTRICIDAD": TriageFallbackContent(
        specific_diagnosis=(
            "Posible falla electrica, fusible, luces o sistema de arranque."
        ),
        suggested_service="Revision electrica basica en sitio.",
        customer_recommendation=(
            "Evita manipular cables o fusibles si no tienes experiencia."
        ),
        operator_notes=(
            "Revisar fusibles, bateria, conectores, luces y tablero."
        ),
    ),
    "GRUA": TriageFallbackContent(
        specific_diagnosis=(
            "Vehiculo posiblemente no apto para continuar circulando."
        ),
        suggested_service="Servicio de grua o traslado asistido.",
        customer_recommendation=(
            "Permanece en un lugar seguro y espera el auxilio."
        ),
        operator_notes=(
            "Verificar accesibilidad para remolque y estado general del vehiculo."
        ),
    ),
    "AIRE ACONDICIONADO": TriageFallbackContent(
        specific_diagnosis="Posible falla del sistema de climatizacion.",
        suggested_service="Revision de aire acondicionado vehicular.",
        customer_recommendation=(
            "Puedes continuar si el vehiculo funciona normalmente, salvo senales de sobrecalentamiento."
        ),
        operator_notes=(
            "Revisar compresor, fugas, refrigerante y ventiladores."
        ),
    ),
    "MECANICA GENERAL": TriageFallbackContent(
        specific_diagnosis=(
            "Posible falla mecanica que requiere revision inicial en sitio."
        ),
        suggested_service="Diagnostico mecanico inicial.",
        customer_recommendation=(
            "No fuerces el vehiculo si se apago, vibra, humea o presenta ruidos anomalos."
        ),
        operator_notes=(
            "Revisar motor, niveles, fugas, temperatura, correas, ruidos y estado general."
        ),
    ),
    "MECANICA": TriageFallbackContent(
        specific_diagnosis=(
            "Posible falla mecanica que requiere revision inicial en sitio."
        ),
        suggested_service="Diagnostico mecanico inicial.",
        customer_recommendation=(
            "No fuerces el vehiculo si se apago, vibra, humea o presenta ruidos anomalos."
        ),
        operator_notes=(
            "Revisar motor, niveles, fugas, temperatura, correas, ruidos y estado general."
        ),
    ),
    GENERAL_DIAGNOSIS_SPECIALTY: TriageFallbackContent(
        specific_diagnosis=(
            "La informacion no permite identificar una falla especifica con seguridad."
        ),
        suggested_service="Diagnostico general en sitio.",
        customer_recommendation=(
            "Espera asistencia y evita mover el vehiculo si no es seguro."
        ),
        operator_notes=(
            "Levantar diagnostico fisico completo antes de iniciar reparacion."
        ),
    ),
}

_DEFAULT_FALLBACK = _FALLBACK_BY_SPECIALTY[GENERAL_DIAGNOSIS_SPECIALTY]
_UNCLEAR_IMAGE_MARKERS = (
    "borros",
    "oscura",
    "oscuro",
    "no relevante",
    "irrelevante",
    "sin detalle",
    "poco clara",
    "poco claro",
    "generica",
    "general",
    "difusa",
)
_SPECIFIC_DESCRIPTION_MARKERS = (
    "llanta",
    "neumatic",
    "goma",
    "pinch",
    "bateria",
    "alternador",
    "arranc",
    "prende",
    "electr",
    "fusible",
    "grua",
    "remol",
    "aire",
    "acondicionado",
    "motor",
    "freno",
    "temperatura",
    "humo",
    "fuga",
    "vibr",
    "ruido",
    "combustible",
)
_VAGUE_DESCRIPTION_MARKERS = (
    "se me paro",
    "se paro",
    "se apago",
    "se quedo",
    "no funciona",
    "tengo un problema",
    "ayuda",
    "revision",
    "revise",
    "revisar",
    "falla general",
)


def normalize_catalog_name(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).replace("_", " ").replace("-", " ").split())
    if not normalized:
        return None
    without_marks = "".join(
        char
        for char in unicodedata.normalize("NFKD", normalized)
        if not unicodedata.combining(char)
    )
    return without_marks.upper()


def build_triage_details_from_ai_result(
    *,
    description: str,
    detected_specialty_name: str | None,
    raw_detected_specialty_name: str | None,
    severity: str | None,
    confidence: Decimal | None,
    summary: str | None,
    specific_diagnosis: str | None,
    suggested_service: str | None,
    customer_recommendation: str | None,
    operator_notes: str | None,
    visual_evidence_tags: Any,
    provider_requires_manual_review: bool | None,
    min_confidence: int,
    image_count: int,
    specialty_override_reason: str | None = None,
    suppress_manual_review_reasons: set[str] | None = None,
) -> TriageDiagnosisDetails:
    fallback = _get_fallback_for_specialty(
        detected_specialty_name or raw_detected_specialty_name
    )
    normalized_tags = normalize_visual_evidence_tags(visual_evidence_tags)
    resolved_specific_diagnosis = _normalize_text(specific_diagnosis) or fallback.specific_diagnosis
    resolved_suggested_service = _normalize_text(suggested_service) or fallback.suggested_service
    resolved_customer_recommendation = (
        _normalize_text(customer_recommendation) or fallback.customer_recommendation
    )
    resolved_operator_notes = _normalize_text(operator_notes) or fallback.operator_notes
    resolved_summary = _resolve_summary(
        summary=summary,
        fallback_specific_diagnosis=resolved_specific_diagnosis,
        fallback_suggested_service=resolved_suggested_service,
    )

    manual_review_reasons: list[str] = []
    manual_review_threshold = max(min_confidence, MANUAL_REVIEW_CONFIDENCE_FLOOR)
    normalized_detected_specialty = normalize_catalog_name(detected_specialty_name)
    normalized_raw_specialty = normalize_catalog_name(raw_detected_specialty_name)

    if detected_specialty_name is None:
        manual_review_reasons.append("specialty_not_mapped")
    if confidence is None or confidence < Decimal(manual_review_threshold):
        manual_review_reasons.append("low_confidence")
    if normalized_detected_specialty == GENERAL_DIAGNOSIS_SPECIALTY:
        manual_review_reasons.append("general_diagnosis")
    if provider_requires_manual_review:
        manual_review_reasons.append("provider_requested_review")
    if _is_description_too_vague(description):
        manual_review_reasons.append("vague_description")
    if _has_unclear_image_signal(
        tags=normalized_tags,
        summary=resolved_summary,
        specific_diagnosis=resolved_specific_diagnosis,
        image_count=image_count,
    ):
        manual_review_reasons.append("unclear_visual_evidence")
    if _is_inconsistent_response(
        raw_detected_specialty_name=raw_detected_specialty_name,
        normalized_raw_specialty=normalized_raw_specialty,
        normalized_detected_specialty=normalized_detected_specialty,
    ):
        manual_review_reasons.append("inconsistent_response")

    if suppress_manual_review_reasons:
        manual_review_reasons = [
            reason
            for reason in manual_review_reasons
            if reason not in suppress_manual_review_reasons
        ]

    return TriageDiagnosisDetails(
        detected_specialty=detected_specialty_name or _normalize_text(raw_detected_specialty_name),
        raw_detected_specialty=_normalize_text(raw_detected_specialty_name),
        mapped_detected_specialty=detected_specialty_name,
        specialty_override_reason=_normalize_text(specialty_override_reason),
        severity=_normalize_text(severity),
        confidence=confidence,
        specific_diagnosis=resolved_specific_diagnosis,
        suggested_service=resolved_suggested_service,
        customer_recommendation=resolved_customer_recommendation,
        operator_notes=resolved_operator_notes,
        visual_evidence_tags=normalized_tags,
        requires_manual_review=bool(manual_review_reasons),
        summary=resolved_summary,
        manual_review_reasons=manual_review_reasons,
    )


def build_triage_details_from_payload(
    *,
    payload: Mapping[str, Any] | None,
    detected_specialty_name: str | None,
    summary: str | None,
    severity: str | None,
    confidence: Decimal | None,
    requires_manual_review: bool,
) -> TriageDiagnosisDetails:
    safe_payload = payload or {}
    resolved_detected_specialty = (
        detected_specialty_name
        or _normalize_text(safe_payload.get("detected_specialty"))
        or _normalize_text(safe_payload.get("especialidad_detectada_nombre"))
    )
    fallback = _get_fallback_for_specialty(resolved_detected_specialty)
    visual_evidence_tags = normalize_visual_evidence_tags(
        safe_payload.get("visual_evidence_tags") or safe_payload.get("etiquetas_imagen")
    )
    resolved_specific_diagnosis = (
        _normalize_text(safe_payload.get("specific_diagnosis"))
        or fallback.specific_diagnosis
    )
    resolved_suggested_service = (
        _normalize_text(safe_payload.get("suggested_service"))
        or fallback.suggested_service
    )
    resolved_customer_recommendation = (
        _normalize_text(safe_payload.get("customer_recommendation"))
        or fallback.customer_recommendation
    )
    resolved_operator_notes = (
        _normalize_text(safe_payload.get("operator_notes"))
        or fallback.operator_notes
    )
    resolved_summary = _resolve_summary(
        summary=summary
        or _normalize_text(safe_payload.get("summary"))
        or _normalize_text(safe_payload.get("resumen")),
        fallback_specific_diagnosis=resolved_specific_diagnosis,
        fallback_suggested_service=resolved_suggested_service,
    )
    manual_review_reasons = _normalize_string_list(
        safe_payload.get("manual_review_reasons")
    )
    payload_requires_manual_review = bool(safe_payload.get("requires_manual_review"))

    return TriageDiagnosisDetails(
        detected_specialty=resolved_detected_specialty,
        raw_detected_specialty=_normalize_text(safe_payload.get("raw_detected_specialty")),
        mapped_detected_specialty=(
            _normalize_text(safe_payload.get("mapped_detected_specialty"))
            or _normalize_text(safe_payload.get("specialty_detected_mapped"))
        ),
        specialty_override_reason=_normalize_text(
            safe_payload.get("specialty_override_reason")
        ),
        severity=_normalize_text(severity)
        or _normalize_text(safe_payload.get("severity"))
        or _normalize_text(safe_payload.get("severidad")),
        confidence=confidence,
        specific_diagnosis=resolved_specific_diagnosis,
        suggested_service=resolved_suggested_service,
        customer_recommendation=resolved_customer_recommendation,
        operator_notes=resolved_operator_notes,
        visual_evidence_tags=visual_evidence_tags,
        requires_manual_review=requires_manual_review or payload_requires_manual_review,
        summary=resolved_summary,
        manual_review_reasons=manual_review_reasons,
    )


def build_triage_payload(
    *,
    raw_provider_result: Mapping[str, Any],
    provider_metadata: Mapping[str, Any],
    details: TriageDiagnosisDetails,
    min_confidence: int,
) -> dict[str, Any]:
    confidence_value = float(details.confidence) if details.confidence is not None else None
    payload = dict(raw_provider_result)
    safe_provider_metadata = {
        "provider": provider_metadata.get("provider"),
        "model": provider_metadata.get("model"),
        "vision_enabled": provider_metadata.get("vision_enabled"),
        "image_count_received_by_backend": provider_metadata.get(
            "image_count_received_by_backend"
        ),
        "image_count_sent_to_ai": provider_metadata.get("image_count_sent_to_ai"),
        "image_mime_types": provider_metadata.get("image_mime_types"),
        "image_bytes_total": provider_metadata.get("image_bytes_total"),
        "used_image_evidence": provider_metadata.get("used_image_evidence"),
        "raw_detected_specialty": details.raw_detected_specialty
        or provider_metadata.get("raw_detected_specialty"),
        "mapped_detected_specialty": details.mapped_detected_specialty,
        "specialty_override_reason": details.specialty_override_reason,
        "visual_evidence_tags": details.visual_evidence_tags,
    }
    payload.update(
        {
            "summary": details.summary,
            "resumen": details.summary,
            "severity": details.severity,
            "severidad": details.severity,
            "detected_specialty": details.detected_specialty,
            "especialidad_detectada_nombre": details.detected_specialty,
            "confidence": confidence_value,
            "confianza": confidence_value,
            "specific_diagnosis": details.specific_diagnosis,
            "suggested_service": details.suggested_service,
            "customer_recommendation": details.customer_recommendation,
            "operator_notes": details.operator_notes,
            "visual_evidence_tags": details.visual_evidence_tags,
            "etiquetas_imagen": details.visual_evidence_tags or None,
            "requires_manual_review": details.requires_manual_review,
            "manual_review_reasons": details.manual_review_reasons,
            "manual_review_reason": (
                details.manual_review_reasons[0]
                if details.manual_review_reasons
                else None
            ),
            "provider": provider_metadata.get("provider"),
            "model": provider_metadata.get("model"),
            "vision_enabled": provider_metadata.get("vision_enabled"),
            "image_count": provider_metadata.get("image_count"),
            "image_count_received_by_backend": provider_metadata.get(
                "image_count_received_by_backend"
            ),
            "image_count_sent_to_ai": provider_metadata.get("image_count_sent_to_ai"),
            "image_mime_types": provider_metadata.get("image_mime_types"),
            "image_bytes_total": provider_metadata.get("image_bytes_total"),
            "used_image_evidence": provider_metadata.get("used_image_evidence"),
            "image_omitted_reason": provider_metadata.get("image_omitted_reason"),
            "audio_included": provider_metadata.get("audio_included"),
            "audio_omitted_reason": provider_metadata.get("audio_omitted_reason"),
            "provider_metadata": safe_provider_metadata,
            "raw_detected_specialty": details.raw_detected_specialty
            or provider_metadata.get("raw_detected_specialty"),
            "mapped_detected_specialty": details.mapped_detected_specialty,
            "specialty_override_reason": details.specialty_override_reason,
            "specialty_detected_mapped": details.detected_specialty,
            "triage_min_confidence": min_confidence,
            "manual_review_confidence_threshold": max(
                min_confidence,
                MANUAL_REVIEW_CONFIDENCE_FLOOR,
            ),
        }
    )
    return payload


def normalize_visual_evidence_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        normalized = _normalize_text(value)
        return [normalized] if normalized else []
    if isinstance(value, Mapping):
        tags: list[str] = []
        for key, item in value.items():
            normalized_key = _normalize_text(key)
            if normalized_key is None:
                continue
            if isinstance(item, bool):
                if item:
                    tags.append(normalized_key)
                continue
            if isinstance(item, (int, float, Decimal)):
                if item > 0:
                    tags.append(normalized_key)
                continue
            rendered_item = _normalize_text(item)
            if rendered_item:
                tags.append(normalized_key)
        return _dedupe_keep_order(tags)
    if isinstance(value, (list, tuple, set)):
        return _normalize_string_list(list(value))
    return []


def _get_fallback_for_specialty(value: Any) -> TriageFallbackContent:
    normalized = normalize_catalog_name(value)
    if normalized is None:
        return _DEFAULT_FALLBACK
    return _FALLBACK_BY_SPECIALTY.get(normalized, _DEFAULT_FALLBACK)


def _is_description_too_vague(description: str) -> bool:
    normalized = normalize_catalog_name(description)
    if normalized is None:
        return True
    lowered = normalized.lower()
    if any(marker in lowered for marker in _SPECIFIC_DESCRIPTION_MARKERS):
        return False
    if any(marker in lowered for marker in _VAGUE_DESCRIPTION_MARKERS):
        return True
    return len(lowered.split()) <= 3


def _has_unclear_image_signal(
    *,
    tags: list[str],
    summary: str | None,
    specific_diagnosis: str | None,
    image_count: int,
) -> bool:
    if image_count <= 0:
        return False
    combined = " ".join(
        item.lower()
        for item in [
            *tags,
            summary or "",
            specific_diagnosis or "",
        ]
        if item
    )
    return any(marker in combined for marker in _UNCLEAR_IMAGE_MARKERS)


def _is_inconsistent_response(
    *,
    raw_detected_specialty_name: str | None,
    normalized_raw_specialty: str | None,
    normalized_detected_specialty: str | None,
) -> bool:
    if raw_detected_specialty_name is not None and normalized_detected_specialty is None:
        return True
    if normalized_raw_specialty is not None and normalized_detected_specialty is None:
        return True
    return False


def _resolve_summary(
    *,
    summary: str | None,
    fallback_specific_diagnosis: str | None,
    fallback_suggested_service: str | None,
) -> str | None:
    normalized_summary = _normalize_text(summary)
    if normalized_summary:
        return normalized_summary
    if fallback_specific_diagnosis:
        return fallback_specific_diagnosis
    return fallback_suggested_service


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized_items = [
        normalized
        for item in value
        if (normalized := _normalize_text(str(item)))
    ]
    return _dedupe_keep_order(normalized_items)


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in values:
        marker = item.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(item)
    return deduped
