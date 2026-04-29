import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class FinalizationTimelineItemModel {
  final DateTime? timestamp;
  final String action;
  final String? previousState;
  final String? newState;
  final String? motivo;
  final int? durationSeconds;

  const FinalizationTimelineItemModel({
    this.timestamp,
    required this.action,
    this.previousState,
    this.newState,
    this.motivo,
    this.durationSeconds,
  });

  factory FinalizationTimelineItemModel.fromJson(Map<String, dynamic> json) {
    return FinalizationTimelineItemModel(
      timestamp: parseDate(json['timestamp']),
      action: json['action'] as String? ?? '',
      previousState: json['previous_state'] as String?,
      newState: json['new_state'] as String?,
      motivo: json['motivo'] as String?,
      durationSeconds: parseNullableInt(json['duration_seconds']),
    );
  }
}

class FinalizationStatusModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final String incidentState;
  final bool reportExists;
  final int finalEvidenceCount;
  final bool finalizationEligible;
  final bool clientDecisionPending;
  final DateTime? confirmedAt;
  final List<FinalizationTimelineItemModel> timeline;

  const FinalizationStatusModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.incidentState,
    required this.reportExists,
    required this.finalEvidenceCount,
    required this.finalizationEligible,
    required this.clientDecisionPending,
    this.confirmedAt,
    required this.timeline,
  });

  factory FinalizationStatusModel.fromJson(Map<String, dynamic> json) {
    final rawTimeline = json['timeline'];
    return FinalizationStatusModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String? ?? '',
      reportExists: json['report_exists'] as bool? ?? false,
      finalEvidenceCount: parseNullableInt(json['final_evidence_count']) ?? 0,
      finalizationEligible: json['finalization_eligible'] as bool? ?? false,
      clientDecisionPending: json['client_decision_pending'] as bool? ?? false,
      confirmedAt: parseDate(json['confirmed_at']),
      timeline: rawTimeline is List
          ? rawTimeline
              .whereType<Map<String, dynamic>>()
              .map(FinalizationTimelineItemModel.fromJson)
              .toList()
          : const [],
    );
  }
}
