import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class FinalizationDecisionResponseModel {
  final int serviceId;
  final String previousState;
  final String newState;
  final int incidentId;
  final String incidentState;
  final DateTime? confirmedAt;
  final int? durationSeconds;
  final int finalEvidenceCount;
  final String message;

  const FinalizationDecisionResponseModel({
    required this.serviceId,
    required this.previousState,
    required this.newState,
    required this.incidentId,
    required this.incidentState,
    this.confirmedAt,
    this.durationSeconds,
    required this.finalEvidenceCount,
    required this.message,
  });

  factory FinalizationDecisionResponseModel.fromJson(
    Map<String, dynamic> json,
  ) {
    return FinalizationDecisionResponseModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      previousState: json['previous_state'] as String? ?? '',
      newState: json['new_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String? ?? '',
      confirmedAt: parseDate(json['confirmed_at']),
      durationSeconds: parseNullableInt(json['duration_seconds']),
      finalEvidenceCount: parseNullableInt(json['final_evidence_count']) ?? 0,
      message: json['message'] as String? ?? '',
    );
  }
}
