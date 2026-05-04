import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class IncidentDiagnosisSummaryModel {
  final int incidentId;
  final String incidentState;
  final double latitud;
  final double longitud;
  final String? clientReportedSpecialty;
  final String? detectedSpecialty;
  final String? severity;
  final double? confidence;
  final String? aiSummary;
  final String? specificDiagnosis;
  final String? suggestedService;
  final String? customerRecommendation;
  final String? operatorNotes;
  final List<String> visualEvidenceTags;
  final String? audioTranscript;
  final dynamic imageTags;
  final bool requiresManualReview;
  final Map<String, dynamic>? aiJson;
  final bool diagnosisReady;

  const IncidentDiagnosisSummaryModel({
    required this.incidentId,
    required this.incidentState,
    required this.latitud,
    required this.longitud,
    this.clientReportedSpecialty,
    this.detectedSpecialty,
    this.severity,
    this.confidence,
    this.aiSummary,
    this.specificDiagnosis,
    this.suggestedService,
    this.customerRecommendation,
    this.operatorNotes,
    this.visualEvidenceTags = const [],
    this.audioTranscript,
    this.imageTags,
    required this.requiresManualReview,
    this.aiJson,
    required this.diagnosisReady,
  });

  factory IncidentDiagnosisSummaryModel.fromJson(Map<String, dynamic> json) {
    final aiJsonRaw = json['diagnostico_ia_json'];

    return IncidentDiagnosisSummaryModel(
      incidentId: parseIntOrZero(json['incident_id']),
      incidentState: json['incident_state'] as String? ?? '',
      latitud: parseDoubleOrZero(json['incident_latitud']),
      longitud: parseDoubleOrZero(json['incident_longitud']),
      clientReportedSpecialty: json['client_reported_specialty'] as String?,
      detectedSpecialty: json['detected_specialty'] as String?,
      severity: json['severity'] as String?,
      confidence: parseNullableDouble(json['confidence']),
      aiSummary: json['ai_summary'] as String?,
      specificDiagnosis: json['specific_diagnosis'] as String?,
      suggestedService: json['suggested_service'] as String?,
      customerRecommendation: json['customer_recommendation'] as String?,
      operatorNotes: json['operator_notes'] as String?,
      visualEvidenceTags: (json['visual_evidence_tags'] as List<dynamic>? ?? [])
          .map((item) => item.toString().trim())
          .where((item) => item.isNotEmpty)
          .toList(),
      audioTranscript: json['transcripcion_audio'] as String?,
      imageTags: json['etiquetas_imagen'],
      requiresManualReview: json['requires_manual_review'] as bool? ?? false,
      aiJson: aiJsonRaw is Map<String, dynamic> ? aiJsonRaw : null,
      diagnosisReady: json['diagnosis_ready'] as bool? ?? false,
    );
  }
}
