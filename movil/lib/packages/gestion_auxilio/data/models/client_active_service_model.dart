import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class ClientActiveServiceModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final String incidentState;
  final String? workshopName;
  final String? operarioName;
  final String? detectedSpecialty;
  final String? aiSummary;
  final String? prequotationCode;
  final double? prequotationMin;
  final double? prequotationMax;
  final String? prequotationCurrency;
  final DateTime? createdAt;
  final DateTime? assignedAt;

  const ClientActiveServiceModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.incidentState,
    this.workshopName,
    this.operarioName,
    this.detectedSpecialty,
    this.aiSummary,
    this.prequotationCode,
    this.prequotationMin,
    this.prequotationMax,
    this.prequotationCurrency,
    this.createdAt,
    this.assignedAt,
  });

  factory ClientActiveServiceModel.fromJson(Map<String, dynamic> json) {
    return ClientActiveServiceModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      incidentState: json['incident_state'] as String? ?? '',
      workshopName: json['workshop_name'] as String?,
      operarioName: json['operario_name'] as String?,
      detectedSpecialty: json['detected_specialty'] as String?,
      aiSummary: json['ai_summary'] as String?,
      prequotationCode: json['prequotation_code'] as String?,
      prequotationMin: parseNullableDouble(json['prequotation_min']),
      prequotationMax: parseNullableDouble(json['prequotation_max']),
      prequotationCurrency: json['prequotation_currency'] as String?,
      createdAt: parseDate(json['created_at']),
      assignedAt: parseDate(json['assigned_at']),
    );
  }
}
