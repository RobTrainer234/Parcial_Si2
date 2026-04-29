import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class OperatorProgressTimelineItemModel {
  final DateTime? timestamp;
  final String action;
  final String? previousState;
  final String? newState;
  final String? observation;

  const OperatorProgressTimelineItemModel({
    this.timestamp,
    required this.action,
    this.previousState,
    this.newState,
    this.observation,
  });

  factory OperatorProgressTimelineItemModel.fromJson(
    Map<String, dynamic> json,
  ) {
    return OperatorProgressTimelineItemModel(
      timestamp: parseDate(json['timestamp']),
      action: json['action'] as String? ?? '',
      previousState: json['previous_state'] as String?,
      newState: json['new_state'] as String?,
      observation: json['observacion'] as String?,
    );
  }
}

class OperatorProgressSnapshotModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final String incidentState;
  final String? detectedSpecialty;
  final String? aiSummary;
  final bool profileAcknowledged;
  final bool arrivalRecorded;
  final List<String> allowedNextStates;
  final List<OperatorProgressTimelineItemModel> timeline;

  const OperatorProgressSnapshotModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.incidentState,
    this.detectedSpecialty,
    this.aiSummary,
    required this.profileAcknowledged,
    required this.arrivalRecorded,
    this.allowedNextStates = const [],
    this.timeline = const [],
  });

  factory OperatorProgressSnapshotModel.fromJson(Map<String, dynamic> json) {
    return OperatorProgressSnapshotModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String? ?? '',
      detectedSpecialty: json['detected_specialty'] as String?,
      aiSummary: json['ai_summary'] as String?,
      profileAcknowledged: json['profile_acknowledged'] as bool? ?? false,
      arrivalRecorded: json['arrival_recorded'] as bool? ?? false,
      allowedNextStates:
          (json['allowed_next_states'] as List<dynamic>? ?? const [])
              .map((item) => item.toString())
              .toList(),
      timeline: (json['timeline'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(OperatorProgressTimelineItemModel.fromJson)
          .toList(),
    );
  }
}

class OperatorProgressResponseModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final String? incidentState;
  final String? previousState;
  final String? newState;
  final DateTime? changedAt;
  final double? currentDistanceMeters;
  final int? arrivalThresholdMeters;
  final bool? hasArrived;
  final int? locationPointId;
  final double? routeDistanceMeters;
  final double? routeDurationSeconds;
  final String message;

  const OperatorProgressResponseModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    this.incidentState,
    this.previousState,
    this.newState,
    this.changedAt,
    this.currentDistanceMeters,
    this.arrivalThresholdMeters,
    this.hasArrived,
    this.locationPointId,
    this.routeDistanceMeters,
    this.routeDurationSeconds,
    required this.message,
  });

  factory OperatorProgressResponseModel.fromJson(Map<String, dynamic> json) {
    final newState = json['new_state'] as String?;
    return OperatorProgressResponseModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState:
          json['service_state'] as String? ?? newState ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String?,
      previousState: json['previous_state'] as String?,
      newState: newState,
      changedAt: parseDate(json['changed_at']) ?? parseDate(json['saved_at']),
      currentDistanceMeters: parseNullableDouble(json['current_distance_meters']),
      arrivalThresholdMeters: parseNullableInt(json['arrival_threshold_meters']),
      hasArrived: json['has_arrived'] as bool?,
      locationPointId: parseNullableInt(json['location_point_id']),
      routeDistanceMeters: parseNullableDouble(json['route_distance_meters']),
      routeDurationSeconds:
          parseNullableDouble(json['route_duration_seconds']),
      message: json['message'] as String? ?? '',
    );
  }
}
