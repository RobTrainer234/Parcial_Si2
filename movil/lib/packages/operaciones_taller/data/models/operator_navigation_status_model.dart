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
  });

  factory OperatorNavigationStatusModel.fromJson(Map<String, dynamic> json) {
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
    );
  }
}
