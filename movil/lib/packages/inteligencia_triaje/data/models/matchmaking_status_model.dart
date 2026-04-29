import 'parse_helpers.dart';
import 'specialty_summary_model.dart';
import 'workshop_candidate_model.dart';

class ActiveRequestModel {
  final int requestId;
  final String requestStatus;
  final int attemptNumber;
  final DateTime? expiresAt;
  final bool usedInsurancePriority;
  final double? proximityScore;
  final double? reputationScore;
  final double? totalScore;
  final WorkshopCandidateModel selectedWorkshop;
  final bool isExpired;

  const ActiveRequestModel({
    required this.requestId,
    required this.requestStatus,
    required this.attemptNumber,
    this.expiresAt,
    required this.usedInsurancePriority,
    this.proximityScore,
    this.reputationScore,
    this.totalScore,
    required this.selectedWorkshop,
    required this.isExpired,
  });

  factory ActiveRequestModel.fromJson(Map<String, dynamic> json) {
    return ActiveRequestModel(
      requestId: parseRequiredInt(json['request_id'], field: 'request_id'),
      requestStatus: json['request_status'] as String? ?? '',
      attemptNumber:
          parseRequiredInt(json['attempt_number'], field: 'attempt_number'),
      expiresAt: parseDate(json['expires_at']),
      usedInsurancePriority: json['used_insurance_priority'] as bool? ?? false,
      proximityScore: parseNullableDouble(json['score_proximidad']),
      reputationScore: parseNullableDouble(json['score_reputacion']),
      totalScore: parseNullableDouble(json['score_total']),
      selectedWorkshop: WorkshopCandidateModel.fromJson(
        (json['selected_workshop'] as Map<String, dynamic>?) ??
            <String, dynamic>{},
      ),
      isExpired: json['is_expired'] as bool? ?? false,
    );
  }
}

class MatchmakingStatusModel {
  final int incidentId;
  final String incidentState;
  final SpecialtySummaryModel? detectedSpecialty;
  final String? severity;
  final ActiveRequestModel? activeRequest;
  final String message;

  const MatchmakingStatusModel({
    required this.incidentId,
    required this.incidentState,
    this.detectedSpecialty,
    this.severity,
    this.activeRequest,
    required this.message,
  });

  factory MatchmakingStatusModel.fromJson(Map<String, dynamic> json) {
    return MatchmakingStatusModel(
      incidentId:
          parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String? ?? '',
      detectedSpecialty: json['detected_specialty'] is Map<String, dynamic>
          ? SpecialtySummaryModel.fromJson(
              json['detected_specialty'] as Map<String, dynamic>,
            )
          : null,
      severity: json['severity'] as String?,
      activeRequest: json['active_request'] is Map<String, dynamic>
          ? ActiveRequestModel.fromJson(
              json['active_request'] as Map<String, dynamic>,
            )
          : null,
      message: json['message'] as String? ?? '',
    );
  }
}
