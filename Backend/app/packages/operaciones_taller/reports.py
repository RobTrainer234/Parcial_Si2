from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, UploadFile, status as http_status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Bitacora, Calificacion, Especialidad, Incidente, Operario, Pago, Servicio, SolicitudServicio
from app.packages.inteligencia_triaje.audio_provider import (
    AudioProviderError,
    AudioProviderNotConfiguredError,
    AudioTranscriptionInput,
    transcribe_audio,
)
from app.packages.seguridad_usuarios.security import utc_now

from .dependencies import WorkshopAccessContext, WorkshopAdminContext
from .schemas import (
    DynamicReportChart,
    DynamicReportChartPoint,
    DynamicReportInsight,
    DynamicReportKpiItem,
    DynamicReportRequest,
    DynamicReportResponse,
    DynamicReportSection,
    DynamicReportTable,
    DynamicReportTableColumn,
    ReportFilterResponse,
    StaticReportSummaryResponse,
    WorkshopReportResponse,
)
from .service import (
    DASHBOARD_ACTIVE_SERVICE_STATES,
    _build_dashboard_operario_query,
    _build_dashboard_request_query,
    _build_dashboard_service_query,
    _get_arrival_start_end,
    _get_dashboard_action_items,
    _get_dashboard_kpis,
    _get_financial_metrics,
    _get_kpi_source_metadata,
    _get_operations_metrics,
    _get_operario_metrics,
    _get_reputation_metrics,
    _get_service_start_reference,
    _get_last_service_location,
    _is_service_location_stale,
    _minutes_between,
    _payment_reference_datetime,
    _validate_dashboard_period,
)


REPORT_ROW_LIMIT = 100
STATIC_REPORTS: dict[str, dict[str, Any]] = {
    "daily_operations": {
        "title": "Reporte diario de operaciones",
        "description": "Emergencias, solicitudes aceptadas, servicios activos, cierres y alertas operativas del día.",
        "default_period": "today",
        "supported_filters": ["date_from", "date_to", "status", "severity", "specialty_id"],
        "source_tables": ["solicitud_servicio", "incidente", "servicio", "taller", "bitacora"],
    },
    "incidents": {
        "title": "Reporte de incidentes",
        "description": "Incidentes por fecha, severidad, especialidad, estado y ubicación.",
        "default_period": "last_30_days",
        "supported_filters": ["date_from", "date_to", "severity", "specialty_id"],
        "source_tables": ["incidente", "solicitud_servicio", "especialidad", "taller"],
    },
    "financial": {
        "title": "Reporte financiero",
        "description": "Ingresos confirmados, pagos pendientes, pagos rechazados y ticket promedio.",
        "default_period": "current_month",
        "supported_filters": ["date_from", "date_to", "status"],
        "source_tables": ["pago", "servicio", "solicitud_servicio", "taller"],
    },
    "sla_response_times": {
        "title": "Reporte SLA y tiempos de respuesta",
        "description": "Tiempos de asignación, llegada, completado y casos fuera de umbral.",
        "default_period": "last_30_days",
        "supported_filters": ["date_from", "date_to", "status", "severity", "specialty_id"],
        "source_tables": ["solicitud_servicio", "servicio", "servicio_ubicacion", "bitacora"],
    },
    "operator_performance": {
        "title": "Reporte de desempeño de operarios",
        "description": "Servicios asignados, completados, tiempo promedio, rating y disponibilidad por operario.",
        "default_period": "last_30_days",
        "supported_filters": ["date_from", "date_to", "status", "specialty_id"],
        "source_tables": ["operario", "persona", "servicio", "calificacion", "taller"],
    },
    "service_quality": {
        "title": "Reporte de calidad del servicio",
        "description": "Calificaciones, servicios mal evaluados y señales de retrabajo o rechazo de finalización.",
        "default_period": "last_30_days",
        "supported_filters": ["date_from", "date_to", "status"],
        "source_tables": ["calificacion", "servicio", "bitacora"],
    },
}
REQUEST_STATUSES = {"PENDIENTE", "ACEPTADA", "RECHAZADA", "EXPIRADA", "CANCELADA", "DESCARTADA"}
SERVICE_STATUSES = {
    "EN_ESPERA_ASIGNACION",
    "ASIGNADO",
    "EN_CAMINO",
    "EN_SITIO",
    "EN_DIAGNOSTICO_FISICO",
    "EN_REPARACION",
    "ESPERANDO_REPUESTOS",
    "COMPLETADO_PENDIENTE_CONFIRMACION",
    "FINALIZADO_PENDIENTE_PAGO",
    "PAGADO",
    "CANCELADO",
}
PAYMENT_STATUSES = {"PENDIENTE", "CONFIRMADO", "RECHAZADO", "ANULADO"}
SEVERITY_KEYWORDS = {
    "critica": "CRITICA",
    "alta": "ALTA",
    "media": "MEDIA",
    "baja": "BAJA",
}
VOICE_REPORT_ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".webm", ".aac", ".ogg"}


@dataclass(slots=True)
class ReportDataset:
    workshop_id: int
    date_from: datetime
    date_to: datetime
    requests: list[SolicitudServicio]
    services: list[Servicio]
    operarios: list[Operario]
    payments: list[Pago]
    ratings: list[Calificacion]
    bitacoras: list[Bitacora]
    bitacoras_by_service_id: dict[int, list[Bitacora]]
    generated_at: datetime


@dataclass(slots=True)
class QueryInterpretation:
    report_type: str
    interpreted_query: str
    date_from: datetime | None
    date_to: datetime | None
    status: str | None
    severity: str | None
    specialty_id: int | None
    warnings: list[str]


@dataclass(slots=True)
class ReportSnapshot:
    kpis: Any
    operations: Any
    financial: Any
    operarios: Any
    reputation: Any
    action_items: list[Any]
    kpi_sources: list[Any]


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _normalize_query_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", _normalize_text(value).lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _start_of_day(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _end_of_day(value: datetime) -> datetime:
    return value.replace(hour=23, minute=59, second=59, microsecond=999999)


def _resolve_static_period(
    *,
    report_type: str,
    date_from: datetime | None,
    date_to: datetime | None,
) -> tuple[datetime, datetime]:
    if date_from is not None or date_to is not None:
        resolved_to = date_to or utc_now()
        resolved_from = date_from or (resolved_to - timedelta(days=30))
        _validate_dashboard_period(date_from=resolved_from, date_to=resolved_to)
        return resolved_from, resolved_to

    now = utc_now()
    default_period = STATIC_REPORTS[report_type]["default_period"]
    if default_period == "today":
        return _start_of_day(now), _end_of_day(now)
    if default_period == "current_month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), _end_of_day(now)
    return now - timedelta(days=30), now


def _between_expr(column: Any, date_from: datetime, date_to: datetime) -> Any:
    return and_(column.is_not(None), column >= date_from, column <= date_to)


def _resolve_service_period_filter(*, date_from: datetime, date_to: datetime) -> Any:
    return or_(
        _between_expr(Servicio.fecha_fin, date_from, date_to),
        _between_expr(Servicio.fecha_inicio, date_from, date_to),
        _between_expr(Servicio.fecha_asignacion_operario, date_from, date_to),
        _between_expr(SolicitudServicio.fecha_respuesta, date_from, date_to),
        _between_expr(SolicitudServicio.fecha_envio, date_from, date_to),
    )


def _resolve_payment_period_filter(*, date_from: datetime, date_to: datetime) -> Any:
    return or_(
        _between_expr(Pago.fecha_confirmacion, date_from, date_to),
        _between_expr(Pago.fecha_solicitud, date_from, date_to),
    )


def _resolve_scope_value(admin_context: WorkshopAdminContext | WorkshopAccessContext) -> str:
    return f"TALLER:{admin_context.workshop_id}"


def _build_filter_response(
    *,
    admin_context: WorkshopAdminContext | WorkshopAccessContext,
    date_from: datetime,
    date_to: datetime,
    status: str | None,
    severity: str | None,
    specialty_id: int | None,
    scope: str | None = None,
) -> ReportFilterResponse:
    return ReportFilterResponse(
        date_from=date_from,
        date_to=date_to,
        scope=scope or _resolve_scope_value(admin_context),
        workshop_id=admin_context.workshop_id,
        status=status,
        severity=severity,
        specialty_id=specialty_id,
    )


def _load_report_dataset(
    *,
    admin_context: WorkshopAdminContext | WorkshopAccessContext,
    db: Session,
    date_from: datetime,
    date_to: datetime,
    status: str | None = None,
    severity: str | None = None,
    specialty_id: int | None = None,
) -> ReportDataset:
    workshop_id = admin_context.workshop_id
    normalized_status = _normalize_text(status).upper() or None
    normalized_severity = _normalize_text(severity).upper() or None

    request_query = (
        _build_dashboard_request_query()
        .join(Incidente, SolicitudServicio.id_incidente == Incidente.id_incidente)
        .where(
            SolicitudServicio.id_taller == workshop_id,
            SolicitudServicio.fecha_envio >= date_from,
            SolicitudServicio.fecha_envio <= date_to,
        )
    )
    if normalized_status in REQUEST_STATUSES:
        request_query = request_query.where(SolicitudServicio.estado == normalized_status)
    if normalized_severity is not None:
        request_query = request_query.where(Incidente.severidad == normalized_severity)
    if specialty_id is not None:
        request_query = request_query.where(
            or_(
                Incidente.id_especialidad_detectada == specialty_id,
                Incidente.id_especialidad_reportada_cliente == specialty_id,
            )
        )
    requests = list(db.scalars(request_query.order_by(SolicitudServicio.fecha_envio.desc())))

    service_query = (
        _build_dashboard_service_query()
        .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
        .join(Incidente, SolicitudServicio.id_incidente == Incidente.id_incidente)
        .where(
            SolicitudServicio.id_taller == workshop_id,
            _resolve_service_period_filter(date_from=date_from, date_to=date_to),
        )
    )
    if normalized_status in SERVICE_STATUSES:
        service_query = service_query.where(Servicio.estado == normalized_status)
    if normalized_severity is not None:
        service_query = service_query.where(Incidente.severidad == normalized_severity)
    if specialty_id is not None:
        service_query = service_query.where(
            or_(
                Incidente.id_especialidad_detectada == specialty_id,
                Incidente.id_especialidad_reportada_cliente == specialty_id,
            )
        )
    services = list(db.scalars(service_query.order_by(Servicio.id_servicio.desc())))

    operarios = list(
        db.scalars(
            _build_dashboard_operario_query()
            .where(Operario.id_taller == workshop_id)
            .order_by(Operario.id_persona.asc())
        )
    )

    payment_query = (
        select(Pago)
        .options(
            joinedload(Pago.servicio)
            .joinedload(Servicio.solicitud)
            .joinedload(SolicitudServicio.incidente),
            joinedload(Pago.servicio).joinedload(Servicio.operario).joinedload(Operario.persona),
            joinedload(Pago.metodo),
        )
        .join(Servicio, Servicio.id_servicio == Pago.id_servicio)
        .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
        .join(Incidente, SolicitudServicio.id_incidente == Incidente.id_incidente)
        .where(
            SolicitudServicio.id_taller == workshop_id,
            _resolve_payment_period_filter(date_from=date_from, date_to=date_to),
        )
    )
    if normalized_status in PAYMENT_STATUSES:
        payment_query = payment_query.where(Pago.estado == normalized_status)
    if normalized_severity is not None:
        payment_query = payment_query.where(Incidente.severidad == normalized_severity)
    if specialty_id is not None:
        payment_query = payment_query.where(
            or_(
                Incidente.id_especialidad_detectada == specialty_id,
                Incidente.id_especialidad_reportada_cliente == specialty_id,
            )
        )
    payments = list(db.scalars(payment_query.order_by(Pago.fecha_solicitud.desc())))

    ratings_query = (
        select(Calificacion)
        .options(
            joinedload(Calificacion.servicio)
            .joinedload(Servicio.solicitud)
            .joinedload(SolicitudServicio.incidente),
            joinedload(Calificacion.servicio).joinedload(Servicio.operario).joinedload(Operario.persona),
        )
        .join(Servicio, Servicio.id_servicio == Calificacion.id_servicio)
        .join(SolicitudServicio, SolicitudServicio.id_solicitud == Servicio.id_solicitud)
        .join(Incidente, SolicitudServicio.id_incidente == Incidente.id_incidente)
        .where(
            SolicitudServicio.id_taller == workshop_id,
            Calificacion.fecha >= date_from,
            Calificacion.fecha <= date_to,
        )
    )
    if normalized_severity is not None:
        ratings_query = ratings_query.where(Incidente.severidad == normalized_severity)
    if specialty_id is not None:
        ratings_query = ratings_query.where(
            or_(
                Incidente.id_especialidad_detectada == specialty_id,
                Incidente.id_especialidad_reportada_cliente == specialty_id,
            )
        )
    ratings = list(db.scalars(ratings_query.order_by(Calificacion.fecha.desc())))

    request_ids = [request.id_solicitud for request in requests]
    service_ids = [service.id_servicio for service in services]
    incident_ids = list({request.id_incidente for request in requests})
    payment_ids = [payment.id_pago for payment in payments]

    bitacora_filters = []
    if request_ids:
        bitacora_filters.append(Bitacora.id_solicitud.in_(request_ids))
    if service_ids:
        bitacora_filters.append(Bitacora.id_servicio.in_(service_ids))
    if incident_ids:
        bitacora_filters.append(Bitacora.id_incidente.in_(incident_ids))
    if payment_ids:
        bitacora_filters.append(Bitacora.id_pago.in_(payment_ids))

    bitacoras = (
        list(
            db.scalars(
                select(Bitacora)
                .where(or_(*bitacora_filters))
                .order_by(Bitacora.fecha_hora.desc(), Bitacora.id_bitacora.desc())
            )
        )
        if bitacora_filters
        else []
    )
    bitacoras_by_service_id: dict[int, list[Bitacora]] = {}
    for event in bitacoras:
        if event.id_servicio is not None:
            bitacoras_by_service_id.setdefault(event.id_servicio, []).append(event)

    return ReportDataset(
        workshop_id=workshop_id,
        date_from=date_from,
        date_to=date_to,
        requests=requests,
        services=services,
        operarios=operarios,
        payments=payments,
        ratings=ratings,
        bitacoras=bitacoras,
        bitacoras_by_service_id=bitacoras_by_service_id,
        generated_at=utc_now(),
    )


def _build_report_snapshot(
    *,
    dataset: ReportDataset,
    db: Session,
) -> ReportSnapshot:
    operations = _get_operations_metrics(
        requests_in_period=dataset.requests,
        services_in_period=dataset.services,
        bitacoras_by_service_id=dataset.bitacoras_by_service_id,
        now=dataset.generated_at,
    )
    financial = _get_financial_metrics(
        services_in_period=dataset.services,
        payments_in_period=dataset.payments,
        date_from=dataset.date_from,
        date_to=dataset.date_to,
    )
    kpis = _get_dashboard_kpis(
        requests_in_period=dataset.requests,
        services_in_period=dataset.services,
        payments_in_period=dataset.payments,
        ratings_in_period=dataset.ratings,
        service_bitacoras_by_service_id=dataset.bitacoras_by_service_id,
        now=dataset.generated_at,
    )
    operarios = _get_operario_metrics(
        operarios=dataset.operarios,
        services_in_period=dataset.services,
        ratings_in_period=dataset.ratings,
    )
    reputation = _get_reputation_metrics(ratings_in_period=dataset.ratings)
    action_items = _get_dashboard_action_items(
        workshop_id=dataset.workshop_id,
        requests_in_period=dataset.requests,
        services_in_period=dataset.services,
        operations=operations,
        financial=financial,
        operarios=dataset.operarios,
        ratings_in_period=dataset.ratings,
        db=db,
        now=dataset.generated_at,
    )
    return ReportSnapshot(
        kpis=kpis,
        operations=operations,
        financial=financial,
        operarios=operarios,
        reputation=reputation,
        action_items=action_items,
        kpi_sources=_get_kpi_source_metadata(),
    )


def _format_number(value: Decimal | int | float | None, decimals: int = 0) -> str:
    if value is None:
        return "Sin datos suficientes"
    if isinstance(value, Decimal):
        numeric = float(value)
    else:
        numeric = float(value)
    return f"{numeric:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_minutes(value: Decimal | int | float | None) -> str:
    if value is None:
        return "Sin datos suficientes"
    return f"{round(float(value))} min"


def _format_currency(value: Decimal | int | float | None) -> str:
    if value is None:
        return "Sin datos suficientes"
    return f"BOB {_format_number(value, 2)}"


def _format_percentage(value: Decimal | int | float | None) -> str:
    if value is None:
        return "Sin datos suficientes"
    return f"{_format_number(value, 1)}%"


def _format_rating(value: Decimal | int | float | None) -> str:
    if value is None:
        return "Sin datos suficientes"
    return f"{_format_number(value, 1)} / 5"


def _make_kpi(
    *,
    key: str,
    label: str,
    value: Decimal | int | float | None,
    display_value: str,
    unit: str | None = None,
) -> DynamicReportKpiItem:
    return DynamicReportKpiItem(
        key=key,
        label=label,
        value=value,
        display_value=display_value,
        unit=unit,
    )


def _warning_if_empty(has_data: bool) -> list[str]:
    return [] if has_data else ["Sin datos suficientes para el periodo seleccionado."]


def _make_count_chart(*, chart_id: str, title: str, items: list[Any], chart_type: str = "BAR") -> DynamicReportChart:
    return DynamicReportChart(
        chart_id=chart_id,
        title=title,
        chart_type=chart_type,
        points=[
            DynamicReportChartPoint(label=str(item.label), value=item.count)
            for item in items
        ],
        empty_message="Sin datos suficientes para el periodo seleccionado.",
    )


def _make_series_chart(
    *,
    chart_id: str,
    title: str,
    points: list[tuple[str, Decimal | int | float | None]],
    chart_type: str = "BAR",
    unit: str | None = None,
) -> DynamicReportChart:
    return DynamicReportChart(
        chart_id=chart_id,
        title=title,
        chart_type=chart_type,
        unit=unit,
        points=[DynamicReportChartPoint(label=label, value=value) for label, value in points],
        empty_message="Sin datos suficientes para el periodo seleccionado.",
    )


def _make_table(
    *,
    table_id: str,
    title: str,
    columns: list[tuple[str, str]],
    rows: list[dict[str, Any]],
    total_count: int,
) -> DynamicReportTable:
    limited_rows = rows[:REPORT_ROW_LIMIT]
    return DynamicReportTable(
        table_id=table_id,
        title=title,
        columns=[DynamicReportTableColumn(key=key, label=label) for key, label in columns],
        rows=limited_rows,
        total_count=total_count,
        limited=total_count > len(limited_rows),
        empty_message="Sin datos suficientes para el periodo seleccionado.",
    )


def _group_counts_by_day(requests: list[SolicitudServicio]) -> list[tuple[str, int]]:
    grouped: dict[str, int] = {}
    for request in requests:
        day_key = request.fecha_envio.astimezone().strftime("%Y-%m-%d")
        grouped[day_key] = grouped.get(day_key, 0) + 1
    return sorted(grouped.items())


def _group_revenue_by_day(payments: list[Pago]) -> list[tuple[str, Decimal]]:
    grouped: dict[str, Decimal] = {}
    for payment in payments:
        reference_dt = _payment_reference_datetime(payment)
        if reference_dt is None or payment.estado != "CONFIRMADO":
            continue
        day_key = reference_dt.astimezone().strftime("%Y-%m-%d")
        grouped[day_key] = grouped.get(day_key, Decimal("0")) + Decimal(payment.monto)
    return sorted(grouped.items())


def _serialize_request_row(request: SolicitudServicio) -> dict[str, Any]:
    incident = request.incidente
    return {
        "fecha": request.fecha_envio.isoformat(),
        "incidente_id": request.id_incidente,
        "solicitud_id": request.id_solicitud,
        "estado_solicitud": request.estado,
        "estado_incidente": incident.estado,
        "severidad": incident.severidad or "SIN_DATO",
        "especialidad": (
            incident.especialidad_detectada.nombre
            if incident.especialidad_detectada is not None
            else "SIN_DATO"
        ),
        "descripcion": incident.descripcion_cliente,
        "ubicacion": f"{incident.latitud}, {incident.longitud}",
    }


def _serialize_payment_row(payment: Pago) -> dict[str, Any]:
    service = payment.servicio
    request = service.solicitud
    return {
        "fecha": (_payment_reference_datetime(payment) or payment.fecha_solicitud).isoformat(),
        "servicio_id": service.id_servicio,
        "incidente_id": request.id_incidente,
        "estado_pago": payment.estado,
        "estado_servicio": service.estado,
        "monto": _format_currency(payment.monto),
        "metodo": payment.metodo.nombre if payment.metodo is not None else "SIN_DATO",
        "operario": (
            f"{service.operario.persona.nombre} {service.operario.persona.apellido}"
            if service.operario is not None and service.operario.persona is not None
            else "Sin asignar"
        ),
    }


def _serialize_operator_row(item: Any) -> dict[str, Any]:
    return {
        "operario_id": item.operario_id,
        "nombre": item.nombre_completo,
        "disponibilidad": item.estado_disponibilidad,
        "servicios_asignados": item.assigned_services,
        "servicios_completados": item.completed_services,
        "rating_promedio": _format_rating(item.average_rating),
        "tiempo_promedio_completado": _format_minutes(item.average_completion_time_minutes),
        "bandera_riesgo": item.risk_flag or "SIN_ALERTA",
    }


def _serialize_quality_row(item: Any) -> dict[str, Any]:
    return {
        "servicio_id": item.service_id,
        "incidente_id": item.incident_id,
        "estrellas": item.stars,
        "comentario": item.comment or "Sin comentario",
        "fecha": item.rated_at.isoformat(),
        "destino": item.rated_target_type,
    }


def _build_daily_operations_report(
    *,
    dataset: ReportDataset,
    snapshot: ReportSnapshot,
    filters: ReportFilterResponse,
) -> WorkshopReportResponse:
    pending_issues = (
        snapshot.kpis.services_without_operator
        + snapshot.kpis.stale_tracking_services
        + len(snapshot.operations.stuck_services)
    )
    has_data = bool(dataset.requests or dataset.services)
    insights = [
        DynamicReportInsight(
            level="HIGH" if pending_issues > 0 else "INFO",
            title="Incidencias pendientes de seguimiento",
            message=(
                f"Se detectaron {pending_issues} alertas operativas activas."
                if pending_issues > 0
                else "No se detectaron alertas críticas en el periodo."
            ),
            recommendation="Revisar asignaciones pendientes, tracking y servicios atascados.",
        )
    ]
    for item in snapshot.action_items[:3]:
        insights.append(
            DynamicReportInsight(
                level=item.priority,
                title=item.title,
                message=item.description,
                recommendation=item.recommended_action,
            )
        )

    return WorkshopReportResponse(
        report_type="daily_operations",
        title=STATIC_REPORTS["daily_operations"]["title"],
        date_from=dataset.date_from,
        date_to=dataset.date_to,
        scope=filters.scope,
        filters=filters,
        summary=(
            f"En el periodo se registraron {len(dataset.requests)} solicitudes, "
            f"{snapshot.kpis.accepted_requests} aceptadas, {snapshot.kpis.active_services} servicios activos "
            f"y {snapshot.kpis.completed_services_count} servicios con cierre registrado."
        ),
        kpis=[
            _make_kpi(key="incidents", label="Emergencias / solicitudes", value=len(dataset.requests), display_value=_format_number(len(dataset.requests))),
            _make_kpi(key="accepted_requests", label="Solicitudes aceptadas", value=snapshot.kpis.accepted_requests, display_value=_format_number(snapshot.kpis.accepted_requests)),
            _make_kpi(key="active_services", label="Servicios activos", value=snapshot.kpis.active_services, display_value=_format_number(snapshot.kpis.active_services)),
            _make_kpi(key="completed_services", label="Servicios completados", value=snapshot.kpis.completed_services_count, display_value=_format_number(snapshot.kpis.completed_services_count)),
            _make_kpi(key="pending_issues", label="Incidencias pendientes", value=pending_issues, display_value=_format_number(pending_issues)),
        ],
        sections=[
            DynamicReportSection(
                section_id="daily_overview",
                title="Resumen operativo diario",
                description="Vista consolidada del flujo de incidentes, aceptación y ejecución.",
                items=[
                    f"Solicitudes pendientes: {snapshot.kpis.pending_requests}",
                    f"Solicitudes rechazadas o expiradas: {snapshot.kpis.rejected_requests + snapshot.kpis.expired_requests}",
                    f"Servicios activos con operario pendiente: {snapshot.kpis.services_without_operator}",
                ],
            )
        ],
        charts=[
            _make_count_chart(chart_id="requests_by_status", title="Solicitudes por estado", items=snapshot.operations.requests_by_status, chart_type="DONUT"),
            _make_count_chart(chart_id="services_by_state", title="Servicios por estado", items=snapshot.operations.services_by_state),
            _make_series_chart(chart_id="daily_incidents", title="Solicitudes por día", points=_group_counts_by_day(dataset.requests), chart_type="LINE"),
        ],
        tables=[
            _make_table(
                table_id="daily_requests",
                title="Detalle de solicitudes del periodo",
                columns=[
                    ("fecha", "Fecha"),
                    ("incidente_id", "Incidente"),
                    ("solicitud_id", "Solicitud"),
                    ("estado_solicitud", "Estado solicitud"),
                    ("estado_incidente", "Estado incidente"),
                    ("severidad", "Severidad"),
                    ("especialidad", "Especialidad"),
                ],
                rows=[_serialize_request_row(request) for request in dataset.requests],
                total_count=len(dataset.requests),
            )
        ],
        insights=insights,
        warnings=_warning_if_empty(has_data),
        source_tables=STATIC_REPORTS["daily_operations"]["source_tables"],
        generated_at=dataset.generated_at,
    )


def _build_incidents_report(
    *,
    dataset: ReportDataset,
    snapshot: ReportSnapshot,
    filters: ReportFilterResponse,
) -> WorkshopReportResponse:
    unique_requests = {request.id_incidente: request for request in dataset.requests}
    incident_rows = list(unique_requests.values())
    critical_count = sum(1 for request in incident_rows if request.incidente.severidad == "CRITICA")
    has_data = bool(incident_rows)
    top_specialty = (
        snapshot.operations.incidents_by_detected_specialty[0].label
        if snapshot.operations.incidents_by_detected_specialty
        else "Sin datos suficientes"
    )
    return WorkshopReportResponse(
        report_type="incidents",
        title=STATIC_REPORTS["incidents"]["title"],
        date_from=dataset.date_from,
        date_to=dataset.date_to,
        scope=filters.scope,
        filters=filters,
        summary=(
            f"Se identificaron {len(incident_rows)} incidentes únicos vinculados al taller. "
            f"{critical_count} fueron críticos y la especialidad más frecuente fue {top_specialty}."
        ),
        kpis=[
            _make_kpi(key="total_incidents", label="Incidentes únicos", value=len(incident_rows), display_value=_format_number(len(incident_rows))),
            _make_kpi(key="critical_incidents", label="Incidentes críticos", value=critical_count, display_value=_format_number(critical_count)),
            _make_kpi(key="pending_incidents", label="Incidentes en proceso", value=sum(1 for request in incident_rows if request.incidente.estado != "FINALIZADO"), display_value=_format_number(sum(1 for request in incident_rows if request.incidente.estado != "FINALIZADO"))),
            _make_kpi(key="manual_review", label="Revisión manual requerida", value=sum(1 for request in incident_rows if request.incidente.requiere_revision_manual), display_value=_format_number(sum(1 for request in incident_rows if request.incidente.requiere_revision_manual))),
        ],
        sections=[
            DynamicReportSection(
                section_id="incidents_focus",
                title="Lectura del periodo",
                description="Concentración de incidentes por severidad, especialidad y estado.",
                items=[
                    f"Top especialidad detectada: {top_specialty}",
                    f"Incidentes con revisión manual: {sum(1 for request in incident_rows if request.incidente.requiere_revision_manual)}",
                    f"Puntos geográficos únicos: {len(snapshot.operations.incident_heatmap_points)}",
                ],
            )
        ],
        charts=[
            _make_count_chart(chart_id="incidents_by_severity", title="Incidentes por severidad", items=snapshot.operations.incidents_by_severity),
            _make_count_chart(chart_id="incidents_by_specialty", title="Incidentes por especialidad", items=snapshot.operations.incidents_by_detected_specialty),
            _make_series_chart(chart_id="incidents_by_day", title="Incidentes por día", points=_group_counts_by_day(incident_rows), chart_type="LINE"),
        ],
        tables=[
            _make_table(
                table_id="incident_detail",
                title="Detalle de incidentes",
                columns=[
                    ("fecha", "Fecha"),
                    ("incidente_id", "Incidente"),
                    ("estado_incidente", "Estado"),
                    ("severidad", "Severidad"),
                    ("especialidad", "Especialidad"),
                    ("ubicacion", "Ubicación"),
                    ("descripcion", "Descripción"),
                ],
                rows=[_serialize_request_row(request) for request in incident_rows],
                total_count=len(incident_rows),
            )
        ],
        insights=[
            DynamicReportInsight(
                level="HIGH" if critical_count > 0 else "INFO",
                title="Incidentes críticos",
                message=(
                    f"Se registraron {critical_count} incidentes críticos en el periodo."
                    if critical_count > 0
                    else "No hubo incidentes críticos en el periodo."
                ),
                recommendation="Priorizar revisión de causas repetidas y tiempos de respuesta en severidad alta o crítica.",
            )
        ],
        warnings=_warning_if_empty(has_data),
        source_tables=STATIC_REPORTS["incidents"]["source_tables"],
        generated_at=dataset.generated_at,
    )


def _build_financial_report(
    *,
    dataset: ReportDataset,
    snapshot: ReportSnapshot,
    filters: ReportFilterResponse,
) -> WorkshopReportResponse:
    has_data = bool(dataset.payments or dataset.services)
    confirmed_revenue_points = _group_revenue_by_day(dataset.payments)
    return WorkshopReportResponse(
        report_type="financial",
        title=STATIC_REPORTS["financial"]["title"],
        date_from=dataset.date_from,
        date_to=dataset.date_to,
        scope=filters.scope,
        filters=filters,
        summary=(
            f"Los ingresos confirmados suman {_format_currency(snapshot.financial.total_revenue)}. "
            f"Hay {snapshot.financial.pending_payments} pagos pendientes y el ticket promedio es {_format_currency(snapshot.financial.average_ticket)}."
        ),
        kpis=[
            _make_kpi(key="confirmed_revenue", label="Ingresos confirmados", value=snapshot.financial.total_revenue, display_value=_format_currency(snapshot.financial.total_revenue), unit="BOB"),
            _make_kpi(key="pending_payments", label="Pagos pendientes", value=snapshot.financial.pending_payments, display_value=_format_number(snapshot.financial.pending_payments)),
            _make_kpi(key="rejected_payments", label="Pagos rechazados", value=snapshot.financial.rejected_payments, display_value=_format_number(snapshot.financial.rejected_payments)),
            _make_kpi(key="average_ticket", label="Ticket promedio", value=snapshot.financial.average_ticket, display_value=_format_currency(snapshot.financial.average_ticket), unit="BOB"),
        ],
        sections=[
            DynamicReportSection(
                section_id="financial_health",
                title="Estado financiero",
                description="Resumen de ingresos, cobros abiertos y comportamiento del ticket.",
                items=[
                    f"Pagos confirmados: {snapshot.financial.confirmed_payments}",
                    f"Pagos pendientes: {snapshot.financial.pending_payments}",
                    f"Pagos rechazados: {snapshot.financial.rejected_payments}",
                ],
            )
        ],
        charts=[
            _make_series_chart(chart_id="revenue_by_day", title="Ingresos confirmados por día", points=confirmed_revenue_points, chart_type="LINE", unit="BOB"),
            _make_series_chart(
                chart_id="payment_status_distribution",
                title="Distribución de pagos",
                points=[
                    ("Confirmados", snapshot.financial.confirmed_payments),
                    ("Pendientes", snapshot.financial.pending_payments),
                    ("Rechazados", snapshot.financial.rejected_payments),
                ],
                chart_type="DONUT",
            ),
        ],
        tables=[
            _make_table(
                table_id="payment_detail",
                title="Detalle de pagos",
                columns=[
                    ("fecha", "Fecha"),
                    ("servicio_id", "Servicio"),
                    ("incidente_id", "Incidente"),
                    ("estado_pago", "Estado pago"),
                    ("estado_servicio", "Estado servicio"),
                    ("monto", "Monto"),
                    ("metodo", "Método"),
                    ("operario", "Operario"),
                ],
                rows=[_serialize_payment_row(payment) for payment in dataset.payments],
                total_count=len(dataset.payments),
            )
        ],
        insights=[
            DynamicReportInsight(
                level="HIGH" if snapshot.financial.pending_payments > 0 else "INFO",
                title="Cobros pendientes",
                message=(
                    f"Hay {snapshot.financial.pending_payments} pagos pendientes de confirmación."
                    if snapshot.financial.pending_payments > 0
                    else "No hay pagos pendientes en el periodo."
                ),
                recommendation="Hacer seguimiento a servicios finalizados pendientes de pago.",
            )
        ],
        warnings=_warning_if_empty(has_data),
        source_tables=STATIC_REPORTS["financial"]["source_tables"],
        generated_at=dataset.generated_at,
    )


def _build_sla_report(
    *,
    dataset: ReportDataset,
    snapshot: ReportSnapshot,
    filters: ReportFilterResponse,
) -> WorkshopReportResponse:
    timing_rows: list[dict[str, Any]] = []
    for service in dataset.services:
        service_bitacoras = dataset.bitacoras_by_service_id.get(service.id_servicio, [])
        arrival_start, arrival_end = _get_arrival_start_end(
            service=service,
            service_bitacoras=service_bitacoras,
        )
        timing_rows.append(
            {
                "servicio_id": service.id_servicio,
                "incidente_id": service.solicitud.id_incidente,
                "estado_servicio": service.estado,
                "tiempo_asignacion": _format_minutes(
                    _minutes_between(service.solicitud.fecha_envio, service.solicitud.fecha_respuesta)
                ),
                "tiempo_asignacion_operario": _format_minutes(
                    _minutes_between(_get_service_start_reference(service), service.fecha_asignacion_operario)
                ),
                "tiempo_llegada": _format_minutes(_minutes_between(arrival_start, arrival_end)),
                "tiempo_completado": _format_minutes(_minutes_between(service.fecha_inicio, service.fecha_fin)),
            }
        )
    has_data = bool(dataset.requests or dataset.services)
    return WorkshopReportResponse(
        report_type="sla_response_times",
        title=STATIC_REPORTS["sla_response_times"]["title"],
        date_from=dataset.date_from,
        date_to=dataset.date_to,
        scope=filters.scope,
        filters=filters,
        summary=(
            f"Tiempo promedio de asignación: {_format_minutes(snapshot.kpis.average_assignment_time_minutes)}. "
            f"Tiempo promedio de llegada: {_format_minutes(snapshot.kpis.average_arrival_time_minutes)}. "
            f"Servicios fuera de umbral de llegada: {snapshot.kpis.services_exceeding_arrival_threshold}."
        ),
        kpis=[
            _make_kpi(key="assignment_avg", label="Tiempo promedio de asignación", value=snapshot.kpis.average_assignment_time_minutes, display_value=_format_minutes(snapshot.kpis.average_assignment_time_minutes), unit="min"),
            _make_kpi(key="operator_assignment_avg", label="Asignación de operario", value=snapshot.kpis.average_operator_assignment_time_minutes, display_value=_format_minutes(snapshot.kpis.average_operator_assignment_time_minutes), unit="min"),
            _make_kpi(key="arrival_avg", label="Tiempo promedio de llegada", value=snapshot.kpis.average_arrival_time_minutes, display_value=_format_minutes(snapshot.kpis.average_arrival_time_minutes), unit="min"),
            _make_kpi(key="completion_avg", label="Tiempo promedio de completado", value=snapshot.kpis.average_completion_time_minutes, display_value=_format_minutes(snapshot.kpis.average_completion_time_minutes), unit="min"),
            _make_kpi(key="arrival_threshold_exceeded", label="Fuera de umbral de llegada", value=snapshot.kpis.services_exceeding_arrival_threshold, display_value=_format_number(snapshot.kpis.services_exceeding_arrival_threshold)),
        ],
        sections=[
            DynamicReportSection(
                section_id="sla_rules",
                title="Definición de tiempos medidos",
                description="Los tiempos siguen la misma lógica exacta del dashboard operativo.",
                items=[
                    "Asignación: fecha_envio -> fecha_respuesta en solicitudes aceptadas.",
                    "Asignación de operario: fecha_respuesta o created_at -> fecha_asignacion_operario.",
                    "Llegada: NAVEGACION_INICIADA -> OPERARIO_EN_SITIO, con fallback a fecha_inicio -> fecha_llegada.",
                    "Completado: fecha_inicio -> fecha_fin.",
                ],
            )
        ],
        charts=[
            _make_series_chart(
                chart_id="sla_averages",
                title="Promedios SLA",
                points=[
                    ("Asignación", snapshot.kpis.average_assignment_time_minutes),
                    ("Asignación operario", snapshot.kpis.average_operator_assignment_time_minutes),
                    ("Llegada", snapshot.kpis.average_arrival_time_minutes),
                    ("Completado", snapshot.kpis.average_completion_time_minutes),
                ],
                unit="min",
            ),
            _make_series_chart(
                chart_id="sla_risks",
                title="Riesgos SLA",
                points=[
                    ("Sin operario", snapshot.kpis.services_without_operator),
                    ("Sin ubicación", snapshot.kpis.services_without_location),
                    ("Tracking stale", snapshot.kpis.stale_tracking_services),
                    ("Excede llegada", snapshot.kpis.services_exceeding_arrival_threshold),
                ],
            ),
        ],
        tables=[
            _make_table(
                table_id="sla_service_detail",
                title="Detalle de tiempos por servicio",
                columns=[
                    ("servicio_id", "Servicio"),
                    ("incidente_id", "Incidente"),
                    ("estado_servicio", "Estado"),
                    ("tiempo_asignacion", "Tiempo asignación"),
                    ("tiempo_asignacion_operario", "Tiempo asignación operario"),
                    ("tiempo_llegada", "Tiempo llegada"),
                    ("tiempo_completado", "Tiempo completado"),
                ],
                rows=timing_rows,
                total_count=len(timing_rows),
            )
        ],
        insights=[
            DynamicReportInsight(
                level="HIGH" if snapshot.kpis.services_exceeding_arrival_threshold > 0 else "INFO",
                title="Cumplimiento de llegada",
                message=(
                    f"{snapshot.kpis.services_exceeding_arrival_threshold} servicios exceden el umbral de llegada."
                    if snapshot.kpis.services_exceeding_arrival_threshold > 0
                    else "No hay servicios excediendo el umbral de llegada."
                ),
                recommendation="Revisar rutas activas, disponibilidad de operarios y incidentes con tracking desactualizado.",
            )
        ],
        warnings=_warning_if_empty(has_data),
        source_tables=STATIC_REPORTS["sla_response_times"]["source_tables"],
        generated_at=dataset.generated_at,
    )


def _build_operator_performance_report(
    *,
    dataset: ReportDataset,
    snapshot: ReportSnapshot,
    filters: ReportFilterResponse,
) -> WorkshopReportResponse:
    operator_rows = snapshot.operarios.operarios
    top_operator = snapshot.operarios.operario_ranking[0] if snapshot.operarios.operario_ranking else None
    availability_counts: dict[str, int] = {}
    for item in operator_rows:
        availability_counts[item.estado_disponibilidad] = availability_counts.get(item.estado_disponibilidad, 0) + 1
    has_data = bool(operator_rows)
    return WorkshopReportResponse(
        report_type="operator_performance",
        title=STATIC_REPORTS["operator_performance"]["title"],
        date_from=dataset.date_from,
        date_to=dataset.date_to,
        scope=filters.scope,
        filters=filters,
        summary=(
            f"Se evaluaron {len(operator_rows)} operarios del taller. "
            f"El mejor desempeño actual corresponde a {top_operator.nombre_completo if top_operator is not None else 'Sin datos suficientes'}."
        ),
        kpis=[
            _make_kpi(key="operators", label="Operarios evaluados", value=len(operator_rows), display_value=_format_number(len(operator_rows))),
            _make_kpi(key="assigned_services", label="Servicios asignados", value=sum(item.assigned_services for item in operator_rows), display_value=_format_number(sum(item.assigned_services for item in operator_rows))),
            _make_kpi(key="completed_services", label="Servicios completados", value=sum(item.completed_services for item in operator_rows), display_value=_format_number(sum(item.completed_services for item in operator_rows))),
            _make_kpi(key="top_rating", label="Mejor rating visible", value=top_operator.average_rating if top_operator is not None else None, display_value=_format_rating(top_operator.average_rating if top_operator is not None else None)),
        ],
        sections=[
            DynamicReportSection(
                section_id="operator_summary",
                title="Cobertura por operario",
                description="Servicios completados, rating y disponibilidad del equipo técnico.",
                items=[
                    f"Operario top: {top_operator.nombre_completo}" if top_operator is not None else "Sin operario top para este periodo.",
                    f"Operarios no disponibles o baja: {sum(1 for item in operator_rows if item.estado_disponibilidad in {'NO_DISPONIBLE', 'BAJA'})}",
                    f"Operarios con bandera de riesgo: {sum(1 for item in operator_rows if item.risk_flag is not None)}",
                ],
            )
        ],
        charts=[
            _make_series_chart(
                chart_id="completed_by_operator",
                title="Servicios completados por operario",
                points=[(item.nombre_completo, item.completed_services) for item in operator_rows],
            ),
            _make_series_chart(
                chart_id="availability_distribution",
                title="Disponibilidad actual",
                points=[(label, count) for label, count in sorted(availability_counts.items())],
                chart_type="DONUT",
            ),
        ],
        tables=[
            _make_table(
                table_id="operator_detail",
                title="Detalle de desempeño por operario",
                columns=[
                    ("operario_id", "Operario"),
                    ("nombre", "Nombre"),
                    ("disponibilidad", "Disponibilidad"),
                    ("servicios_asignados", "Asignados"),
                    ("servicios_completados", "Completados"),
                    ("rating_promedio", "Rating"),
                    ("tiempo_promedio_completado", "Tiempo promedio"),
                    ("bandera_riesgo", "Bandera riesgo"),
                ],
                rows=[_serialize_operator_row(item) for item in operator_rows],
                total_count=len(operator_rows),
            )
        ],
        insights=[
            DynamicReportInsight(
                level="INFO" if top_operator is not None else "LOW",
                title="Operario destacado",
                message=(
                    f"{top_operator.nombre_completo} lidera el ranking con {top_operator.completed_services} servicios completados."
                    if top_operator is not None
                    else "No hay datos suficientes para determinar un operario destacado."
                ),
                recommendation="Usar el ranking para balancear carga y revisar capacitación de operarios con menor cierre.",
            )
        ],
        warnings=_warning_if_empty(has_data),
        source_tables=STATIC_REPORTS["operator_performance"]["source_tables"],
        generated_at=dataset.generated_at,
    )


def _build_service_quality_report(
    *,
    dataset: ReportDataset,
    snapshot: ReportSnapshot,
    filters: ReportFilterResponse,
) -> WorkshopReportResponse:
    rejected_finalizations = sum(
        1
        for event_list in dataset.bitacoras_by_service_id.values()
        for event in event_list
        if event.accion == "FINALIZACION_RECHAZADA_CLIENTE"
    )
    has_data = bool(dataset.ratings or rejected_finalizations)
    return WorkshopReportResponse(
        report_type="service_quality",
        title=STATIC_REPORTS["service_quality"]["title"],
        date_from=dataset.date_from,
        date_to=dataset.date_to,
        scope=filters.scope,
        filters=filters,
        summary=(
            f"El rating promedio visible del taller es {_format_rating(snapshot.reputation.workshop_average_rating)}. "
            f"Se detectaron {len(snapshot.reputation.low_rating_services)} servicios con baja calificación y {rejected_finalizations} rechazos de finalización."
        ),
        kpis=[
            _make_kpi(key="average_rating", label="Rating promedio", value=snapshot.reputation.workshop_average_rating, display_value=_format_rating(snapshot.reputation.workshop_average_rating)),
            _make_kpi(key="total_ratings", label="Total calificaciones", value=snapshot.reputation.total_ratings, display_value=_format_number(snapshot.reputation.total_ratings)),
            _make_kpi(key="low_ratings", label="Servicios mal evaluados", value=len(snapshot.reputation.low_rating_services), display_value=_format_number(len(snapshot.reputation.low_rating_services))),
            _make_kpi(key="rejected_finalizations", label="Finalizaciones rechazadas", value=rejected_finalizations, display_value=_format_number(rejected_finalizations)),
        ],
        sections=[
            DynamicReportSection(
                section_id="quality_summary",
                title="Señales de calidad",
                description="Seguimiento de calificaciones bajas y rechazo de cierres.",
                items=[
                    f"Calificaciones registradas: {snapshot.reputation.total_ratings}",
                    f"Servicios con 1 o 2 estrellas: {len(snapshot.reputation.low_rating_services)}",
                    f"Eventos de finalización rechazada: {rejected_finalizations}",
                ],
            )
        ],
        charts=[
            _make_count_chart(chart_id="rating_distribution", title="Distribución de calificaciones", items=snapshot.reputation.rating_distribution, chart_type="DONUT"),
            _make_series_chart(
                chart_id="quality_risks",
                title="Indicadores de calidad",
                points=[
                    ("Baja calificación", len(snapshot.reputation.low_rating_services)),
                    ("Finalización rechazada", rejected_finalizations),
                ],
            ),
        ],
        tables=[
            _make_table(
                table_id="low_rating_detail",
                title="Servicios con baja calificación",
                columns=[
                    ("servicio_id", "Servicio"),
                    ("incidente_id", "Incidente"),
                    ("estrellas", "Estrellas"),
                    ("comentario", "Comentario"),
                    ("fecha", "Fecha"),
                    ("destino", "Destino"),
                ],
                rows=[_serialize_quality_row(item) for item in snapshot.reputation.low_rating_services],
                total_count=len(snapshot.reputation.low_rating_services),
            )
        ],
        insights=[
            DynamicReportInsight(
                level="HIGH" if len(snapshot.reputation.low_rating_services) > 0 or rejected_finalizations > 0 else "INFO",
                title="Riesgo de retrabajo o disconformidad",
                message=(
                    "Existen señales de calidad que requieren seguimiento."
                    if len(snapshot.reputation.low_rating_services) > 0 or rejected_finalizations > 0
                    else "No se detectan señales fuertes de retrabajo o disconformidad en el periodo."
                ),
                recommendation="Revisar comentarios de clientes y eventos de rechazo de finalización para prevención de recurrencias.",
            )
        ],
        warnings=_warning_if_empty(has_data),
        source_tables=STATIC_REPORTS["service_quality"]["source_tables"],
        generated_at=dataset.generated_at,
    )


def _build_report_by_type(
    *,
    report_type: str,
    admin_context: WorkshopAdminContext | WorkshopAccessContext,
    db: Session,
    date_from: datetime | None,
    date_to: datetime | None,
    status: str | None = None,
    severity: str | None = None,
    specialty_id: int | None = None,
    scope: str | None = None,
) -> WorkshopReportResponse:
    if report_type not in STATIC_REPORTS:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Static report type not found.")
    resolved_from, resolved_to = _resolve_static_period(
        report_type=report_type,
        date_from=date_from,
        date_to=date_to,
    )
    filters = _build_filter_response(
        admin_context=admin_context,
        date_from=resolved_from,
        date_to=resolved_to,
        status=_normalize_text(status).upper() or None,
        severity=_normalize_text(severity).upper() or None,
        specialty_id=specialty_id,
        scope=scope,
    )
    dataset = _load_report_dataset(
        admin_context=admin_context,
        db=db,
        date_from=resolved_from,
        date_to=resolved_to,
        status=filters.status,
        severity=filters.severity,
        specialty_id=specialty_id,
    )
    snapshot = _build_report_snapshot(dataset=dataset, db=db)
    if report_type == "daily_operations":
        return _build_daily_operations_report(dataset=dataset, snapshot=snapshot, filters=filters)
    if report_type == "incidents":
        return _build_incidents_report(dataset=dataset, snapshot=snapshot, filters=filters)
    if report_type == "financial":
        return _build_financial_report(dataset=dataset, snapshot=snapshot, filters=filters)
    if report_type == "sla_response_times":
        return _build_sla_report(dataset=dataset, snapshot=snapshot, filters=filters)
    if report_type == "operator_performance":
        return _build_operator_performance_report(dataset=dataset, snapshot=snapshot, filters=filters)
    return _build_service_quality_report(dataset=dataset, snapshot=snapshot, filters=filters)


def list_static_reports() -> list[StaticReportSummaryResponse]:
    return [
        StaticReportSummaryResponse(
            report_type=report_type,
            title=metadata["title"],
            description=metadata["description"],
            default_period=metadata["default_period"],
            supported_filters=list(metadata["supported_filters"]),
        )
        for report_type, metadata in STATIC_REPORTS.items()
    ]


def get_static_report(
    *,
    report_type: str,
    admin_context: WorkshopAdminContext | WorkshopAccessContext,
    db: Session,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: str | None = None,
    severity: str | None = None,
    specialty_id: int | None = None,
) -> WorkshopReportResponse:
    return _build_report_by_type(
        report_type=report_type,
        admin_context=admin_context,
        db=db,
        date_from=date_from,
        date_to=date_to,
        status=status,
        severity=severity,
        specialty_id=specialty_id,
    )


def _resolve_specialty_from_query(db: Session, normalized_query: str) -> int | None:
    specialties = list(db.scalars(select(Especialidad)))
    for specialty in specialties:
        normalized_name = _normalize_query_text(specialty.nombre)
        if normalized_name and normalized_name in normalized_query:
            return specialty.id_especialidad
    return None


def _resolve_named_period_from_query(normalized_query: str) -> tuple[datetime | None, datetime | None]:
    now = utc_now()
    padded_query = f" {normalized_query} "

    def has_phrase(*phrases: str) -> bool:
        return any(f" {phrase} " in padded_query for phrase in phrases)

    if has_phrase("hoy", "hoy dia", "del dia"):
        return _start_of_day(now), _end_of_day(now)
    if has_phrase("ayer"):
        yesterday = now - timedelta(days=1)
        return _start_of_day(yesterday), _end_of_day(yesterday)
    if has_phrase("esta semana", "semanal"):
        week_start = _start_of_day(now - timedelta(days=now.weekday()))
        return week_start, _end_of_day(now)
    if has_phrase("este mes", "mensual"):
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), _end_of_day(now)
    return None, None


def _interpret_dynamic_query(
    *,
    query: str,
    explicit_date_from: datetime | None,
    explicit_date_to: datetime | None,
    db: Session,
) -> QueryInterpretation:
    normalized_query = _normalize_query_text(query)
    warnings: list[str] = []
    report_type = "daily_operations"

    if any(term in normalized_query for term in ("accidente", "accidentes", "incidente", "incidentes", "emergencia", "emergencias")):
        report_type = "incidents"
    elif any(term in normalized_query for term in ("monto", "ingresos", "recaudacion", "recaudacion", "financiero", "finanzas", "pagos", "ticket")):
        report_type = "financial"
    elif any(term in normalized_query for term in ("sla", "llegada", "asignacion", "tiempo de respuesta", "sin operario", "tracking")):
        report_type = "sla_response_times"
    elif any(term in normalized_query for term in ("operario", "operarios", "tecnico", "tecnicos")):
        report_type = "operator_performance"
    elif any(term in normalized_query for term in ("calificacion", "calificaciones", "calidad", "rechazo", "retrabajo", "queja")):
        report_type = "service_quality"
    elif any(term in normalized_query for term in ("activo", "activos", "finalizados", "pendientes", "operacion", "operaciones", "resumen")):
        report_type = "daily_operations"

    resolved_from = explicit_date_from
    resolved_to = explicit_date_to
    if resolved_from is None and resolved_to is None:
        resolved_from, resolved_to = _resolve_named_period_from_query(normalized_query)

    severity = next(
        (value for keyword, value in SEVERITY_KEYWORDS.items() if keyword in normalized_query),
        None,
    )
    specialty_id = _resolve_specialty_from_query(db, normalized_query)

    status_value = None
    status_keywords = {
        "en camino": "EN_CAMINO",
        "en sitio": "EN_SITIO",
        "asignado": "ASIGNADO",
        "pagado": "PAGADO",
        "rechazado": "RECHAZADO",
        "expirado": "EXPIRADA",
        "pendiente de pago": "PENDIENTE",
    }
    for keyword, mapped_status in status_keywords.items():
        if keyword in normalized_query:
            status_value = mapped_status
            break

    if any(term in normalized_query for term in ("talleres", "sucursales", "sucursal")):
        warnings.append("La consulta se limitó al taller autorizado actualmente.")

    interpreted_parts = [STATIC_REPORTS[report_type]["title"]]
    if resolved_from is not None and resolved_to is not None:
        interpreted_parts.append(
            f"periodo {resolved_from.date().isoformat()} -> {resolved_to.date().isoformat()}"
        )
    if severity is not None:
        interpreted_parts.append(f"severidad {severity}")
    if specialty_id is not None:
        interpreted_parts.append(f"especialidad {specialty_id}")
    if status_value is not None:
        interpreted_parts.append(f"estado {status_value}")

    return QueryInterpretation(
        report_type=report_type,
        interpreted_query=" | ".join(interpreted_parts),
        date_from=resolved_from,
        date_to=resolved_to,
        status=status_value,
        severity=severity,
        specialty_id=specialty_id,
        warnings=warnings,
    )


def generate_dynamic_text_report(
    *,
    payload: DynamicReportRequest,
    admin_context: WorkshopAdminContext | WorkshopAccessContext,
    db: Session,
) -> DynamicReportResponse:
    interpretation = _interpret_dynamic_query(
        query=payload.query,
        explicit_date_from=payload.date_from,
        explicit_date_to=payload.date_to,
        db=db,
    )
    report = _build_report_by_type(
        report_type=interpretation.report_type,
        admin_context=admin_context,
        db=db,
        date_from=interpretation.date_from,
        date_to=interpretation.date_to,
        status=interpretation.status,
        severity=interpretation.severity,
        specialty_id=interpretation.specialty_id,
        scope=payload.scope or "TALLER",
    )
    warnings = list(report.warnings)
    warnings.extend(interpretation.warnings)
    return DynamicReportResponse(
        **report.model_dump(exclude={"warnings"}),
        interpreted_query=interpretation.interpreted_query,
        transcription=None,
        warnings=warnings,
    )


def generate_dynamic_audio_report(
    *,
    admin_context: WorkshopAdminContext | WorkshopAccessContext,
    db: Session,
    audio_file: UploadFile,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    scope: str | None = None,
) -> DynamicReportResponse:
    filename = audio_file.filename or "audio-report"
    extension = os.path.splitext(filename)[1].lower()
    if extension and extension not in VOICE_REPORT_ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio format for dynamic report.",
        )
    audio_bytes = audio_file.file.read()
    warnings: list[str] = []
    try:
        transcription = transcribe_audio(
            audio_input=AudioTranscriptionInput(
                content_bytes=audio_bytes,
                filename=filename,
                mime_type=audio_file.content_type or "application/octet-stream",
            ),
            prompt="Transcribe una solicitud de reporte de negocio en espanol.",
        )
        query_text = transcription.transcript_text
        if transcription.warning:
            warnings.append(transcription.warning)
    except (AudioProviderError, AudioProviderNotConfiguredError):
        query_text = None
        warnings.append("No se pudo transcribir el audio. Intenta nuevamente con una grabación más clara.")

    if not query_text:
        resolved_from, resolved_to = _resolve_static_period(
            report_type="daily_operations",
            date_from=date_from,
            date_to=date_to,
        )
        empty_filters = _build_filter_response(
            admin_context=admin_context,
            date_from=resolved_from,
            date_to=resolved_to,
            status=None,
            severity=None,
            specialty_id=None,
            scope=scope or "TALLER",
        )
        return DynamicReportResponse(
            report_type="daily_operations",
            title="Reporte dinámico por audio",
            interpreted_query="Sin interpretación disponible",
            transcription=None,
            date_from=resolved_from,
            date_to=resolved_to,
            scope=empty_filters.scope,
            filters=empty_filters,
            summary="No se pudo obtener una transcripción útil del audio.",
            kpis=[],
            sections=[],
            charts=[],
            tables=[],
            insights=[],
            warnings=warnings or ["Sin datos suficientes para el periodo seleccionado."],
            source_tables=[],
            generated_at=utc_now(),
        )

    report = generate_dynamic_text_report(
        payload=DynamicReportRequest(
            query=query_text,
            date_from=date_from,
            date_to=date_to,
            scope=scope or "TALLER",
        ),
        admin_context=admin_context,
        db=db,
    )
    merged_warnings = list(report.warnings)
    merged_warnings.extend(warnings)
    return DynamicReportResponse(
        **report.model_dump(exclude={"warnings", "transcription"}),
        transcription=query_text,
        warnings=merged_warnings,
    )
