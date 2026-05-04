import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class OperatorEvidenceSummaryModel {
  final int total;
  final int images;
  final int audio;

  const OperatorEvidenceSummaryModel({
    required this.total,
    required this.images,
    required this.audio,
  });

  factory OperatorEvidenceSummaryModel.fromJson(Map<String, dynamic> json) {
    return OperatorEvidenceSummaryModel(
      total: parseIntOrZero(json['total']),
      images: parseIntOrZero(json['imagenes']),
      audio: parseIntOrZero(json['audio']),
    );
  }
}

class OperatorServiceDetailModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final String incidentState;
  final double? latitud;
  final double? longitud;
  final String? workshopName;
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
  final dynamic imageLabels;
  final List<String> suggestedTools;
  final bool? requiresTow;
  final String? observations;
  final String? prequotationCode;
  final double? prequotationMin;
  final double? prequotationMax;
  final String? prequotationCurrency;
  final bool requiresManualReview;
  final OperatorEvidenceSummaryModel evidenceSummary;

  const OperatorServiceDetailModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.incidentState,
    this.latitud,
    this.longitud,
    this.workshopName,
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
    this.imageLabels,
    this.suggestedTools = const [],
    this.requiresTow,
    this.observations,
    this.prequotationCode,
    this.prequotationMin,
    this.prequotationMax,
    this.prequotationCurrency,
    required this.requiresManualReview,
    required this.evidenceSummary,
  });

  factory OperatorServiceDetailModel.fromJson(Map<String, dynamic> json) {
    return OperatorServiceDetailModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String? ?? '',
      latitud: parseNullableDouble(json['latitud']),
      longitud: parseNullableDouble(json['longitud']),
      workshopName: _workshopName(json['workshop']),
      clientReportedSpecialty: _specialtyName(json['client_reported_specialty']),
      detectedSpecialty: _specialtyName(json['detected_specialty']),
      severity: json['severity'] as String?,
      confidence: parseNullableDouble(json['confidence']),
      aiSummary: (json['summary'] as String?) ?? (json['ai_summary'] as String?),
      specificDiagnosis: json['specific_diagnosis'] as String?,
      suggestedService: json['suggested_service'] as String?,
      customerRecommendation: json['customer_recommendation'] as String?,
      operatorNotes: json['operator_notes'] as String?,
      visualEvidenceTags: (json['visual_evidence_tags'] as List<dynamic>? ?? [])
          .map((item) => item.toString().trim())
          .where((item) => item.isNotEmpty)
          .toList(),
      imageLabels: json['etiquetas_imagen'],
      suggestedTools: (json['herramientas_sugeridas'] as List<dynamic>? ?? [])
          .map((item) => item.toString())
          .where((item) => item.trim().isNotEmpty)
          .toList(),
      requiresTow: json['requiere_grua'] as bool?,
      observations: json['observaciones'] as String?,
      prequotationCode: json['prequotation_code'] as String?,
      prequotationMin: parseNullableDouble(json['prequotation_min']),
      prequotationMax: parseNullableDouble(json['prequotation_max']),
      prequotationCurrency: json['prequotation_currency'] as String?,
      requiresManualReview: json['requiere_revision_manual'] as bool? ?? false,
      evidenceSummary: OperatorEvidenceSummaryModel.fromJson(
        (json['evidence_summary'] as Map<String, dynamic>?) ??
            <String, dynamic>{},
      ),
    );
  }
}

String? _specialtyName(dynamic value) {
  if (value is Map<String, dynamic>) {
    final name = value['nombre'];
    if (name is String && name.trim().isNotEmpty) {
      return name;
    }
  }
  return null;
}

String? _workshopName(dynamic value) {
  if (value is Map<String, dynamic>) {
    final name = value['nombre_comercial'];
    if (name is String && name.trim().isNotEmpty) {
      return name;
    }
  }
  return null;
}
