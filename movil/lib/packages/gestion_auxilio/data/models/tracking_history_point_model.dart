import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class TrackingHistoryPointModel {
  final double? latitud;
  final double? longitud;
  final DateTime? fechaHora;

  const TrackingHistoryPointModel({
    this.latitud,
    this.longitud,
    this.fechaHora,
  });

  factory TrackingHistoryPointModel.fromJson(Map<String, dynamic> json) {
    return TrackingHistoryPointModel(
      latitud: parseNullableDouble(json['latitud']),
      longitud: parseNullableDouble(json['longitud']),
      fechaHora: parseDate(json['fecha_hora']),
    );
  }
}
