class PersonaProfileModel {
  final String nombre;
  final String apellido;
  final String ci;
  final String? telefono;
  final String? direccion;

  const PersonaProfileModel({
    required this.nombre,
    required this.apellido,
    required this.ci,
    this.telefono,
    this.direccion,
  });

  factory PersonaProfileModel.fromJson(Map<String, dynamic> json) {
    return PersonaProfileModel(
      nombre: json['nombre'] as String,
      apellido: json['apellido'] as String,
      ci: json['ci'] as String,
      telefono: json['telefono'] as String?,
      direccion: json['direccion'] as String?,
    );
  }
}
