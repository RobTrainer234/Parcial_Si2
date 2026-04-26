from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt

from app.models import Taller


FOUR_DECIMALS = Decimal("0.0001")


@dataclass(frozen=True)
class RankedWorkshopCandidate:
    taller: Taller
    distance_km: Decimal
    score_proximidad: Decimal
    score_reputacion: Decimal
    score_total: Decimal
    used_insurance_priority: bool


def _quantize(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(FOUR_DECIMALS, rounding=ROUND_HALF_UP)


def haversine_distance_km(
    *,
    lat1: Decimal,
    lon1: Decimal,
    lat2: Decimal,
    lon2: Decimal,
) -> Decimal:
    earth_radius_km = 6371.0
    lat1_rad, lon1_rad = radians(float(lat1)), radians(float(lon1))
    lat2_rad, lon2_rad = radians(float(lat2)), radians(float(lon2))
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return _quantize(earth_radius_km * c)


def build_ranked_candidate(
    *,
    incident_lat: Decimal,
    incident_lon: Decimal,
    taller: Taller,
    used_insurance_priority: bool,
) -> RankedWorkshopCandidate:
    distance_km = haversine_distance_km(
        lat1=incident_lat,
        lon1=incident_lon,
        lat2=taller.latitud,
        lon2=taller.longitud,
    )
    radio_accion = Decimal(taller.radio_accion_km)
    if radio_accion <= 0:
        score_proximidad = Decimal("0")
    else:
        proximity_raw = max(0.0, 1.0 - (float(distance_km) / float(radio_accion)))
        score_proximidad = _quantize(proximity_raw)
    reputacion_prom = Decimal(taller.reputacion_prom or 0)
    score_reputacion = _quantize(reputacion_prom / Decimal("5"))
    score_total = _quantize(
        (score_proximidad * Decimal("0.4")) + (score_reputacion * Decimal("0.6"))
    )
    return RankedWorkshopCandidate(
        taller=taller,
        distance_km=distance_km,
        score_proximidad=score_proximidad,
        score_reputacion=score_reputacion,
        score_total=score_total,
        used_insurance_priority=used_insurance_priority,
    )


def candidate_sort_key(candidate: RankedWorkshopCandidate) -> tuple[int, Decimal, Decimal, int]:
    return (
        0 if candidate.used_insurance_priority else 1,
        -candidate.score_total,
        candidate.distance_km,
        candidate.taller.id_taller,
    )
