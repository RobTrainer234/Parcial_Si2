import 'parse_helpers.dart';
import 'specialty_summary_model.dart';
import 'workshop_candidate_model.dart';

class MatchmakingSelectionModel {
  final int incidentId;
  final String previousState;
  final String newState;
  final SpecialtySummaryModel? detectedSpecialty;
  final String? severity;
  final WorkshopCandidateModel? selectedWorkshop;
  final bool? usedInsurancePriority;
  final int? requestId;
  final String? requestStatus;
  final DateTime? expiresAt;
  final double? proximityScore;
  final double? reputationScore;
  final double? totalScore;
  final double? distanceKm;
  final int? attemptNumber;
  final bool noCandidate;
  final String message;

  const MatchmakingSelectionModel({
    required this.incidentId,
    required this.previousState,
    required this.newState,
    this.detectedSpecialty,
    this.severity,
    this.selectedWorkshop,
    this.usedInsurancePriority,
    this.requestId,
    this.requestStatus,
    this.expiresAt,
    this.proximityScore,
    this.reputationScore,
    this.totalScore,
    this.distanceKm,
    this.attemptNumber,
    required this.noCandidate,
    required this.message,
  });

  factory MatchmakingSelectionModel.fromJson(Map<String, dynamic> json) {
    return MatchmakingSelectionModel(
      incidentId:
          parseRequiredInt(json['incident_id'], field: 'incident_id'),
      previousState: json['previous_state'] as String? ?? '',
      newState: json['new_state'] as String? ?? '',
      detectedSpecialty: json['detected_specialty'] is Map<String, dynamic>
          ? SpecialtySummaryModel.fromJson(
              json['detected_specialty'] as Map<String, dynamic>,
            )
          : null,
      severity: json['severity'] as String?,
      selectedWorkshop: json['selected_workshop'] is Map<String, dynamic>
          ? WorkshopCandidateModel.fromJson(
              json['selected_workshop'] as Map<String, dynamic>,
            )
          : null,
      usedInsurancePriority: json['used_insurance_priority'] as bool?,
      requestId: parseNullableInt(json['request_id']),
      requestStatus: json['request_status'] as String?,
      expiresAt: parseDate(json['expires_at']),
      proximityScore: parseNullableDouble(json['score_proximidad']),
      reputationScore: parseNullableDouble(json['score_reputacion']),
      totalScore: parseNullableDouble(json['score_total']),
      distanceKm: parseNullableDouble(json['distance_km']),
      attemptNumber: parseNullableInt(json['attempt_number']),
      noCandidate: json['no_candidate'] as bool? ?? false,
      message: json['message'] as String? ?? '',
    );
  }
}
