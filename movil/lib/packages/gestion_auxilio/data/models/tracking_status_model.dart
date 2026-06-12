import '../../../inteligencia_triaje/data/models/parse_helpers.dart';
import 'package:latlong2/latlong.dart';

class TrackingStatusModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final double incidentLatitud;
  final double incidentLongitud;
  final double? lastOperarioLatitud;
  final double? lastOperarioLongitud;
  final DateTime? lastLocationAt;
  final bool hasLiveLocation;
  final bool locationStale;
  final double? currentDistanceMeters;
  final int? etaSeconds;
  final String? etaText;
  final double? routeDistanceMeters;
  final double? routeDurationSeconds;
  final List<LatLng>? routePoints;
  final String trackingMessage;

  const TrackingStatusModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.incidentLatitud,
    required this.incidentLongitud,
    this.lastOperarioLatitud,
    this.lastOperarioLongitud,
    this.lastLocationAt,
    required this.hasLiveLocation,
    required this.locationStale,
    this.currentDistanceMeters,
    this.etaSeconds,
    this.etaText,
    this.routeDistanceMeters,
    this.routeDurationSeconds,
    this.routePoints,
    required this.trackingMessage,
  });

  factory TrackingStatusModel.fromJson(Map<String, dynamic> json) {
    return TrackingStatusModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentLatitud: parseDoubleOrZero(json['incident_latitud']),
      incidentLongitud: parseDoubleOrZero(json['incident_longitud']),
      lastOperarioLatitud: parseNullableDouble(json['last_operario_latitud']),
      lastOperarioLongitud: parseNullableDouble(json['last_operario_longitud']),
      lastLocationAt: parseDate(json['last_location_at']),
      hasLiveLocation: json['has_live_location'] as bool? ?? false,
      locationStale: json['location_stale'] as bool? ?? false,
      currentDistanceMeters: parseNullableDouble(json['current_distance_meters']),
      etaSeconds: parseNullableInt(json['eta_seconds']),
      etaText: json['eta_text'] as String?,
      routeDistanceMeters: parseNullableDouble(json['route_distance_meters']),
      routeDurationSeconds: parseNullableDouble(json['route_duration_seconds']),
      routePoints: _parseRoutePoints(json['route_points']),
      trackingMessage: json['tracking_message'] as String? ?? '',
    );
  }

  TrackingStatusModel copyWith({
    String? serviceState,
    int? incidentId,
    double? incidentLatitud,
    double? incidentLongitud,
    double? lastOperarioLatitud,
    double? lastOperarioLongitud,
    DateTime? lastLocationAt,
    bool? hasLiveLocation,
    bool? locationStale,
    double? currentDistanceMeters,
    int? etaSeconds,
    String? etaText,
    double? routeDistanceMeters,
    double? routeDurationSeconds,
    List<LatLng>? routePoints,
    String? trackingMessage,
  }) {
    return TrackingStatusModel(
      serviceId: serviceId,
      serviceState: serviceState ?? this.serviceState,
      incidentId: incidentId ?? this.incidentId,
      incidentLatitud: incidentLatitud ?? this.incidentLatitud,
      incidentLongitud: incidentLongitud ?? this.incidentLongitud,
      lastOperarioLatitud: lastOperarioLatitud ?? this.lastOperarioLatitud,
      lastOperarioLongitud: lastOperarioLongitud ?? this.lastOperarioLongitud,
      lastLocationAt: lastLocationAt ?? this.lastLocationAt,
      hasLiveLocation: hasLiveLocation ?? this.hasLiveLocation,
      locationStale: locationStale ?? this.locationStale,
      currentDistanceMeters: currentDistanceMeters ?? this.currentDistanceMeters,
      etaSeconds: etaSeconds ?? this.etaSeconds,
      etaText: etaText ?? this.etaText,
      routeDistanceMeters: routeDistanceMeters ?? this.routeDistanceMeters,
      routeDurationSeconds: routeDurationSeconds ?? this.routeDurationSeconds,
      routePoints: routePoints ?? this.routePoints,
      trackingMessage: trackingMessage ?? this.trackingMessage,
    );
  }
}

List<LatLng>? _parseRoutePoints(dynamic raw) {
  if (raw is! List) {
    return null;
  }
  final points = <LatLng>[];
  for (final item in raw) {
    if (item is List && item.length >= 2) {
      final lat = parseNullableDouble(item[0]);
      final lng = parseNullableDouble(item[1]);
      if (lat != null && lng != null) {
        points.add(LatLng(lat, lng));
      }
    }
  }
  return points.length >= 2 ? points : null;
}
