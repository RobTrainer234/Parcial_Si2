import 'parse_helpers.dart';
import 'specialty_summary_model.dart';

class IncidentDetailModel {
  final int incidentId;
  final String status;
  final DateTime? fechaHora;
  final double latitud;
  final double longitud;
  final String descripcionCliente;
  final int vehicleId;
  final SpecialtySummaryModel reportedSpecialty;
  final SpecialtySummaryModel? detectedSpecialty;
  final String? severity;
  final String? aiSummary;
  final String? specificDiagnosis;
  final String? suggestedService;
  final String? customerRecommendation;
  final String? operatorNotes;
  final List<String> visualEvidenceTags;
  final Map<String, dynamic>? aiJson;
  final double? confidence;
  final String? audioTranscript;
  final String? audioSummary;
  final String audioAnalysisType;
  final dynamic imageTags;
  final DateTime? triageAt;
  final bool requiresManualReview;
  final int evidenceTotal;
  final int imageCount;
  final int audioCount;

  const IncidentDetailModel({
    required this.incidentId,
    required this.status,
    this.fechaHora,
    required this.latitud,
    required this.longitud,
    required this.descripcionCliente,
    required this.vehicleId,
    required this.reportedSpecialty,
    this.detectedSpecialty,
    this.severity,
    this.aiSummary,
    this.specificDiagnosis,
    this.suggestedService,
    this.customerRecommendation,
    this.operatorNotes,
    this.visualEvidenceTags = const [],
    this.aiJson,
    this.confidence,
    this.audioTranscript,
    this.audioSummary,
    this.audioAnalysisType = 'NO_AUDIO',
    this.imageTags,
    this.triageAt,
    required this.requiresManualReview,
    this.evidenceTotal = 0,
    this.imageCount = 0,
    this.audioCount = 0,
  });

  bool get hasPersistedDiagnosis =>
      triageAt != null && detectedSpecialty != null && aiJson != null;

  bool get needsClassification =>
      status == 'EN_TRIAJE' || !hasPersistedDiagnosis;

  bool get isDiagnosed => hasPersistedDiagnosis;

  int get imageCountReceivedByBackend =>
      parseIntOrZero(aiJson?['image_count_received_by_backend']);

  int get imageCountSentToAi =>
      parseIntOrZero(aiJson?['image_count_sent_to_ai']);

  bool get usedImageEvidence => _parseBool(aiJson?['used_image_evidence']);

  bool get visionEnabled => _parseBool(aiJson?['vision_enabled']);

  bool get imageEvidenceAnalyzed =>
      imageCountReceivedByBackend > 0 &&
      imageCountSentToAi > 0 &&
      usedImageEvidence;

  bool get imageEvidenceNotSentToAi =>
      imageCountReceivedByBackend > 0 && imageCountSentToAi == 0;

  bool get hasExperimentalAudioAnalysis =>
      audioAnalysisType == 'MECHANICAL_SOUND_EXPERIMENTAL';

  factory IncidentDetailModel.fromJson(Map<String, dynamic> json) {
    final evidenceSummary = json['evidence_summary'] as Map<String, dynamic>?;
    final aiJsonRaw = json['diagnostico_ia_json'];
    final aiJson = aiJsonRaw is Map<String, dynamic> ? aiJsonRaw : null;
    final detectedSpecialty =
        json['especialidad_detectada'] is Map<String, dynamic>
        ? SpecialtySummaryModel.fromJson(
            json['especialidad_detectada'] as Map<String, dynamic>,
          )
        : null;
    final triageAt = parseDate(json['fecha_triaje']);
    final hasPersistedDiagnosis =
        triageAt != null && detectedSpecialty != null && aiJson != null;

    return IncidentDetailModel(
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      status: json['status'] as String? ?? '',
      fechaHora: parseDate(json['fecha_hora']),
      latitud: parseDoubleOrZero(json['latitud']),
      longitud: parseDoubleOrZero(json['longitud']),
      descripcionCliente: json['descripcion_cliente'] as String? ?? '',
      vehicleId: parseRequiredInt(json['id_vehiculo'], field: 'id_vehiculo'),
      reportedSpecialty: SpecialtySummaryModel.fromJson(
        (json['especialidad_reportada'] as Map<String, dynamic>?) ??
            <String, dynamic>{},
      ),
      detectedSpecialty: detectedSpecialty,
      severity: hasPersistedDiagnosis ? json['severity'] as String? : null,
      aiSummary: hasPersistedDiagnosis
          ? (json['summary'] as String?) ??
                (json['diagnostico_ia_resumen'] as String?) ??
                (aiJson['summary'] as String?) ??
                (aiJson['resumen'] as String?)
          : null,
      specificDiagnosis: hasPersistedDiagnosis
          ? (json['specific_diagnosis'] as String?) ??
                (aiJson['specific_diagnosis'] as String?)
          : null,
      suggestedService: hasPersistedDiagnosis
          ? (json['suggested_service'] as String?) ??
                (aiJson['suggested_service'] as String?)
          : null,
      customerRecommendation: hasPersistedDiagnosis
          ? (json['customer_recommendation'] as String?) ??
                (aiJson['customer_recommendation'] as String?)
          : null,
      operatorNotes: hasPersistedDiagnosis
          ? (json['operator_notes'] as String?) ??
                (aiJson['operator_notes'] as String?)
          : null,
      visualEvidenceTags: hasPersistedDiagnosis
          ? _parseVisualEvidenceTags(
              json['visual_evidence_tags'] ?? aiJson['visual_evidence_tags'],
            )
          : const [],
      aiJson: aiJson,
      confidence: hasPersistedDiagnosis
          ? parseNullableDouble(json['confianza_ia'])
          : null,
      audioTranscript: json['transcripcion_audio'] as String?,
      audioSummary: (json['audio_summary'] as String?) ??
          (aiJson?['audio_summary'] as String?) ??
          (aiJson?['resumen_audio'] as String?),
      audioAnalysisType: (json['audio_analysis_type'] as String?) ??
          (aiJson?['audio_analysis_type'] as String?) ??
          'NO_AUDIO',
      imageTags: json['etiquetas_imagen'],
      triageAt: triageAt,
      requiresManualReview: hasPersistedDiagnosis
          ? json['requiere_revision_manual'] as bool? ?? false
          : false,
      evidenceTotal: parseIntOrZero(evidenceSummary?['total']),
      imageCount: parseIntOrZero(evidenceSummary?['imagenes']),
      audioCount: parseIntOrZero(evidenceSummary?['audio']),
    );
  }
}

bool _parseBool(dynamic value) {
  if (value is bool) {
    return value;
  }
  if (value is String) {
    return value.trim().toLowerCase() == 'true';
  }
  return false;
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
