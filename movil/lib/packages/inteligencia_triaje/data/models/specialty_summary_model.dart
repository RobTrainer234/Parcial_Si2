import 'parse_helpers.dart';

class SpecialtySummaryModel {
  final int idEspecialidad;
  final String nombre;

  const SpecialtySummaryModel({
    required this.idEspecialidad,
    required this.nombre,
  });

  factory SpecialtySummaryModel.fromJson(Map<String, dynamic> json) {
    return SpecialtySummaryModel(
      idEspecialidad:
          parseRequiredInt(json['id_especialidad'], field: 'id_especialidad'),
      nombre: json['nombre'] as String? ?? '',
    );
  }
}
