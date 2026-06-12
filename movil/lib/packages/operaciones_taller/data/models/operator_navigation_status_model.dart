import 'package:latlong2/latlong.dart';

import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class OperatorNavigationStatusModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final String incidentState;
  final double? destinationLatitud;
  final double? destinationLongitud;
  final double? lastKnownLatitud;
  final double? lastKnownLongitud;
  final DateTime? lastKnownAt;
  final double? currentDistanceMeters;
  final bool profileAcknowledged;
  final bool hasArrived;
  final int? arrivalThresholdMeters;
  final String message;
  final double? routeDistanceMeters;
  final double? routeDurationSeconds;
  final List<LatLng>? routePoints;

  const OperatorNavigationStatusModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.incidentState,
    this.destinationLatitud,
    this.destinationLongitud,
    this.lastKnownLatitud,
    this.lastKnownLongitud,
    this.lastKnownAt,
    this.currentDistanceMeters,
    required this.profileAcknowledged,
    required this.hasArrived,
    this.arrivalThresholdMeters,
    required this.message,
    this.routeDistanceMeters,
    this.routeDurationSeconds,
    this.routePoints,
  });

  factory OperatorNavigationStatusModel.fromJson(Map<String, dynamic> json) {
    final routeGeometry = json['route_geometry'];
    final routePoints = _parseRouteGeometry(routeGeometry);

    return OperatorNavigationStatusModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String? ?? '',
      destinationLatitud: parseNullableDouble(json['destination_latitud']),
      destinationLongitud: parseNullableDouble(json['destination_longitud']),
      lastKnownLatitud: parseNullableDouble(json['last_known_latitud']),
      lastKnownLongitud: parseNullableDouble(json['last_known_longitud']),
      lastKnownAt: parseDate(json['last_known_at']),
      currentDistanceMeters: parseNullableDouble(json['current_distance_meters']),
      profileAcknowledged: json['profile_acknowledged'] as bool? ?? false,
      hasArrived: json['has_arrived'] as bool? ?? false,
      arrivalThresholdMeters: parseNullableInt(json['arrival_threshold_meters']),
      message: json['message'] as String? ?? '',
      routeDistanceMeters: parseNullableDouble(json['route_distance_meters']),
      routeDurationSeconds: parseNullableDouble(json['route_duration_seconds']),
      routePoints: routePoints,
    );
  }
}

List<LatLng>? _parseRouteGeometry(dynamic geometry) {
  if (geometry == null) return null;
  if (geometry is Map<String, dynamic>) {
    final type = geometry['type'] as String?;
    final coordinates = geometry['coordinates'];
    if (type == 'LineString' && coordinates is List) {
      final points = <LatLng>[];
      for (final coord in coordinates) {
        if (coord is List && coord.length >= 2) {
          final lng = (coord[0] as num).toDouble();
          final lat = (coord[1] as num).toDouble();
          points.add(LatLng(lat, lng));
        }
      }
      if (points.length >= 2) return points;
    }
  }
  if (geometry is List) {
    try {
      final points = <LatLng>[];
      for (final coord in geometry) {
        if (coord is List && coord.length >= 2) {
          points.add(LatLng(
            (coord[1] as num).toDouble(),
            (coord[0] as num).toDouble(),
          ));
        }
      }
      if (points.length >= 2) return points;
    } catch (_) {}
  }
  return null;
}
