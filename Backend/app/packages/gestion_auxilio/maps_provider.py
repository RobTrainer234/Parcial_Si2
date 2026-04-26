from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings


settings = get_settings()


class RouteProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class NormalizedRouteStep:
    distance_meters: Decimal
    duration_seconds: Decimal
    name: str | None
    maneuver_type: str | None
    maneuver_modifier: str | None
    instruction: str | None


@dataclass(frozen=True)
class NormalizedRoute:
    provider: str
    distance_meters: Decimal
    duration_seconds: Decimal
    geometry: dict[str, object] | list[object] | str | None
    steps: list[NormalizedRouteStep]
    provider_route_id: str | None = None


def _build_step_instruction(step: dict) -> str | None:
    maneuver = step.get("maneuver") or {}
    maneuver_type = maneuver.get("type")
    modifier = maneuver.get("modifier")
    name = step.get("name")
    parts = [part for part in (maneuver_type, modifier, name) if part]
    if not parts:
        return None
    return " | ".join(str(part) for part in parts)


def get_route(
    *,
    origin_lat: Decimal,
    origin_lon: Decimal,
    dest_lat: Decimal,
    dest_lon: Decimal,
) -> NormalizedRoute:
    if settings.maps_provider != "osrm":
        raise RouteProviderError("Configured maps provider is not supported.")

    coordinates = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    query = urlencode(
        {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
        }
    )
    base_url = settings.maps_base_url.rstrip("/")
    url = f"{base_url}/route/v1/driving/{coordinates}?{query}"
    request = Request(url, headers={"Accept": "application/json"})

    try:
        with urlopen(request, timeout=settings.navigation_provider_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RouteProviderError("Route provider request failed.") from exc
    except json.JSONDecodeError as exc:
        raise RouteProviderError("Route provider returned invalid JSON.") from exc

    routes = payload.get("routes") or []
    if not routes:
        raise RouteProviderError("Route provider did not return any route.")

    route = routes[0]
    legs = route.get("legs") or []
    steps: list[NormalizedRouteStep] = []
    for leg in legs:
        for step in leg.get("steps") or []:
            maneuver = step.get("maneuver") or {}
            steps.append(
                NormalizedRouteStep(
                    distance_meters=Decimal(str(step.get("distance", 0))),
                    duration_seconds=Decimal(str(step.get("duration", 0))),
                    name=step.get("name"),
                    maneuver_type=maneuver.get("type"),
                    maneuver_modifier=maneuver.get("modifier"),
                    instruction=_build_step_instruction(step),
                )
            )

    return NormalizedRoute(
        provider="osrm",
        provider_route_id=route.get("weight_name"),
        distance_meters=Decimal(str(route.get("distance", 0))),
        duration_seconds=Decimal(str(route.get("duration", 0))),
        geometry=route.get("geometry"),
        steps=steps,
    )
