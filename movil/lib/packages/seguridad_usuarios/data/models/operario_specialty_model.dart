class OperarioSpecialtyModel {
  final int idEspecialidad;
  final String nombre;
  final int aniosExperiencia;
  final String? certificacionUrl;

  const OperarioSpecialtyModel({
    required this.idEspecialidad,
    required this.nombre,
    required this.aniosExperiencia,
    this.certificacionUrl,
  });

  factory OperarioSpecialtyModel.fromJson(Map<String, dynamic> json) {
    return OperarioSpecialtyModel(
      idEspecialidad: json['id_especialidad'] as int,
      nombre: json['nombre'] as String,
      aniosExperiencia: json['anios_experiencia'] as int? ?? 0,
      certificacionUrl: json['certificacion_url'] as String?,
    );
  }
}
