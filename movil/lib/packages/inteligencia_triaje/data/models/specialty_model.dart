class SpecialtyModel {
  final int idEspecialidad;
  final String nombre;
  final String? descripcion;
  final int? nivelComplejidad;

  const SpecialtyModel({
    required this.idEspecialidad,
    required this.nombre,
    this.descripcion,
    this.nivelComplejidad,
  });

  factory SpecialtyModel.fromJson(Map<String, dynamic> json) {
    final id = _parseRequiredPositiveInt(json['id_especialidad']);
    final nombre = (json['nombre'] as String?)?.trim() ?? '';
    if (nombre.isEmpty) {
      throw const FormatException('nombre inválido');
    }

    return SpecialtyModel(
      idEspecialidad: id,
      nombre: nombre,
      descripcion: (json['descripcion'] as String?)?.trim(),
      nivelComplejidad: _parseNullableInt(json['nivel_complejidad']),
    );
  }

  static int _parseRequiredPositiveInt(dynamic value) {
    final parsed = _parseNullableInt(value);
    if (parsed == null || parsed <= 0) {
      throw const FormatException('id_especialidad inválido');
    }
    return parsed;
  }

  static int? _parseNullableInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value.trim());
    return null;
  }
}
