import 'incident_evidence_model.dart';

class IncidentReportResponseModel {
  final int incidentId;
  final String status;
  final String message;
  final int vehicleId;
  final double latitud;
  final double longitud;
  final String descripcionCliente;
  final String? especialidadNombre;
  final int? especialidadId;
  final DateTime? fechaHora;
  final List<IncidentEvidenceModel> evidences;

  const IncidentReportResponseModel({
    required this.incidentId,
    required this.status,
    required this.message,
    required this.vehicleId,
    required this.latitud,
    required this.longitud,
    required this.descripcionCliente,
    this.especialidadNombre,
    this.especialidadId,
    this.fechaHora,
    this.evidences = const [],
  });

  factory IncidentReportResponseModel.fromJson(Map<String, dynamic> json) {
    final especialidad = json['especialidad_reportada'] as Map<String, dynamic>?;
    final evidenceList = json['evidences'] as List<dynamic>? ?? [];

    return IncidentReportResponseModel(
      incidentId: json['incident_id'] as int,
      status: json['status'] as String? ?? '',
      message: json['message'] as String? ?? '',
      vehicleId: json['id_vehiculo'] as int,
      latitud: _parseDouble(json['latitud']),
      longitud: _parseDouble(json['longitud']),
      descripcionCliente: json['descripcion_cliente'] as String? ?? '',
      especialidadNombre: especialidad?['nombre'] as String?,
      especialidadId: especialidad?['id_especialidad'] as int?,
      fechaHora: json['fecha_hora'] != null
          ? DateTime.tryParse(json['fecha_hora'].toString())
          : null,
      evidences: evidenceList
          .map((e) => IncidentEvidenceModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  static double _parseDouble(dynamic value) {
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0.0;
    return 0.0;
  }
}
