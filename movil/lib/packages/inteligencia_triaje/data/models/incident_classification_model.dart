import 'parse_helpers.dart';
import 'specialty_summary_model.dart';

class IncidentClassificationModel {
  final int incidentId;
  final String previousState;
  final String newState;
  final SpecialtySummaryModel reportedSpecialty;
  final SpecialtySummaryModel? detectedSpecialty;
  final String? severity;
  final double? confidence;
  final bool requiresManualReview;
  final String? summary;
  final String? specificDiagnosis;
  final String? suggestedService;
  final String? customerRecommendation;
  final String? operatorNotes;
  final List<String> visualEvidenceTags;

  const IncidentClassificationModel({
    required this.incidentId,
    required this.previousState,
    required this.newState,
    required this.reportedSpecialty,
    this.detectedSpecialty,
    this.severity,
    this.confidence,
    required this.requiresManualReview,
    this.summary,
    this.specificDiagnosis,
    this.suggestedService,
    this.customerRecommendation,
    this.operatorNotes,
    this.visualEvidenceTags = const [],
  });

  factory IncidentClassificationModel.fromJson(Map<String, dynamic> json) {
    return IncidentClassificationModel(
      incidentId:
          parseRequiredInt(json['incident_id'], field: 'incident_id'),
      previousState: json['previous_state'] as String? ?? '',
      newState: json['new_state'] as String? ?? '',
      reportedSpecialty: SpecialtySummaryModel.fromJson(
        (json['reported_specialty'] as Map<String, dynamic>?) ??
            <String, dynamic>{},
      ),
      detectedSpecialty: json['detected_specialty'] is Map<String, dynamic>
          ? SpecialtySummaryModel.fromJson(
              json['detected_specialty'] as Map<String, dynamic>,
            )
          : null,
      severity: json['severity'] as String?,
      confidence: parseNullableDouble(json['confidence']),
      requiresManualReview: json['requires_manual_review'] as bool? ?? false,
      summary: json['summary'] as String?,
      specificDiagnosis: json['specific_diagnosis'] as String?,
      suggestedService: json['suggested_service'] as String?,
      customerRecommendation: json['customer_recommendation'] as String?,
      operatorNotes: json['operator_notes'] as String?,
      visualEvidenceTags: _parseVisualEvidenceTags(json['visual_evidence_tags']),
    );
  }
}

List<String> _parseVisualEvidenceTags(dynamic value) {
  if (value is List) {
    return value
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList();
  }
  return const [];
}
