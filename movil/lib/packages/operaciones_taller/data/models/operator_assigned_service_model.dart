import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class OperatorAssignedServiceModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final String incidentState;
  final String? detectedSpecialty;
  final String? severity;
  final String? aiSummary;
  final String? prequotationCode;
  final double? prequotationMin;
  final double? prequotationMax;
  final String? prequotationCurrency;

  const OperatorAssignedServiceModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.incidentState,
    this.detectedSpecialty,
    this.severity,
    this.aiSummary,
    this.prequotationCode,
    this.prequotationMin,
    this.prequotationMax,
    this.prequotationCurrency,
  });

  factory OperatorAssignedServiceModel.fromJson(Map<String, dynamic> json) {
    return OperatorAssignedServiceModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String? ?? '',
      detectedSpecialty: _specialtyName(json['detected_specialty']),
      severity: json['severity'] as String?,
      aiSummary: json['ai_summary'] as String?,
      prequotationCode: json['prequotation_code'] as String?,
      prequotationMin: parseNullableDouble(json['prequotation_min']),
      prequotationMax: parseNullableDouble(json['prequotation_max']),
      prequotationCurrency: json['prequotation_currency'] as String?,
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
