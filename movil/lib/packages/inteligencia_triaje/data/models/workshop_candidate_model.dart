import 'parse_helpers.dart';

class WorkshopCandidateModel {
  final int workshopId;
  final String workshopName;
  final double? reputation;
  final double? actionRadiusKm;
  final double? distanceKm;

  const WorkshopCandidateModel({
    required this.workshopId,
    required this.workshopName,
    this.reputation,
    this.actionRadiusKm,
    this.distanceKm,
  });

  factory WorkshopCandidateModel.fromJson(Map<String, dynamic> json) {
    return WorkshopCandidateModel(
      workshopId: parseIntOrZero(json['id_taller']),
      workshopName: json['nombre_comercial'] as String? ?? '',
      reputation: parseNullableDouble(json['reputacion_prom']),
      actionRadiusKm: parseNullableDouble(json['radio_accion_km']),
      distanceKm: parseNullableDouble(json['distance_km']),
    );
  }
}
