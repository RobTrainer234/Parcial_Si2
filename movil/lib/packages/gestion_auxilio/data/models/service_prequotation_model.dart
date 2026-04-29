import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class ServicePrequotationModel {
  final int serviceId;
  final int incidentId;
  final String? prequotationCode;
  final double? prequotationMin;
  final double? prequotationMax;
  final String? prequotationCurrency;
  final String? catalogServiceName;
  final bool? incluyeRepuestosBasicos;
  final String message;

  const ServicePrequotationModel({
    required this.serviceId,
    required this.incidentId,
    this.prequotationCode,
    this.prequotationMin,
    this.prequotationMax,
    this.prequotationCurrency,
    this.catalogServiceName,
    this.incluyeRepuestosBasicos,
    required this.message,
  });

  factory ServicePrequotationModel.fromJson(Map<String, dynamic> json) {
    return ServicePrequotationModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      prequotationCode: json['prequotation_code'] as String?,
      prequotationMin: parseNullableDouble(json['prequotation_min']),
      prequotationMax: parseNullableDouble(json['prequotation_max']),
      prequotationCurrency: json['prequotation_currency'] as String?,
      catalogServiceName: json['catalog_service_name'] as String?,
      incluyeRepuestosBasicos: json['incluye_repuestos_basicos'] as bool?,
      message: json['message'] as String? ?? '',
    );
  }
}
