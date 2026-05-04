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
    this.imageTags,
    this.triageAt,
    required this.requiresManualReview,
    this.evidenceTotal = 0,
    this.imageCount = 0,
    this.audioCount = 0,
  });

  bool get isDiagnosed =>
      triageAt != null || aiSummary != null || detectedSpecialty != null;

  factory IncidentDetailModel.fromJson(Map<String, dynamic> json) {
    final evidenceSummary = json['evidence_summary'] as Map<String, dynamic>?;
    final aiJsonRaw = json['diagnostico_ia_json'];
    final aiJson = aiJsonRaw is Map<String, dynamic> ? aiJsonRaw : null;

    return IncidentDetailModel(
      incidentId:
          parseRequiredInt(json['incident_id'], field: 'incident_id'),
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
      detectedSpecialty: json['especialidad_detectada'] is Map<String, dynamic>
          ? SpecialtySummaryModel.fromJson(
              json['especialidad_detectada'] as Map<String, dynamic>,
            )
          : null,
      severity: json['severity'] as String?,
      aiSummary: (json['summary'] as String?) ??
          (json['diagnostico_ia_resumen'] as String?) ??
          (aiJson?['summary'] as String?) ??
          (aiJson?['resumen'] as String?),
      specificDiagnosis: (json['specific_diagnosis'] as String?) ??
          (aiJson?['specific_diagnosis'] as String?),
      suggestedService: (json['suggested_service'] as String?) ??
          (aiJson?['suggested_service'] as String?),
      customerRecommendation:
          (json['customer_recommendation'] as String?) ??
              (aiJson?['customer_recommendation'] as String?),
      operatorNotes: (json['operator_notes'] as String?) ??
          (aiJson?['operator_notes'] as String?),
      visualEvidenceTags: _parseVisualEvidenceTags(
        json['visual_evidence_tags'] ?? aiJson?['visual_evidence_tags'],
      ),
      aiJson: aiJson,
      confidence: parseNullableDouble(json['confianza_ia']),
      audioTranscript: json['transcripcion_audio'] as String?,
      imageTags: json['etiquetas_imagen'],
      triageAt: parseDate(json['fecha_triaje']),
      requiresManualReview: json['requiere_revision_manual'] as bool? ?? false,
      evidenceTotal: parseIntOrZero(evidenceSummary?['total']),
      imageCount: parseIntOrZero(evidenceSummary?['imagenes']),
      audioCount: parseIntOrZero(evidenceSummary?['audio']),
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
