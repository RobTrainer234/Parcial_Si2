import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

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
      trackingMessage: json['tracking_message'] as String? ?? '',
    );
  }
}
