class ProfileUpdateRequestModel {
  final String? nombre;
  final String? apellido;
  final String? telefono;
  final String? direccion;
  final bool clearTelefono;
  final bool clearDireccion;

  const ProfileUpdateRequestModel({
    this.nombre,
    this.apellido,
    this.telefono,
    this.direccion,
    this.clearTelefono = false,
    this.clearDireccion = false,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{};
    if (nombre != null) map['nombre'] = nombre!.trim();
    if (apellido != null) map['apellido'] = apellido!.trim();
    if (clearTelefono) {
      map['telefono'] = null;
    } else if (telefono != null) {
      map['telefono'] = telefono!.trim();
    }
    if (clearDireccion) {
      map['direccion'] = null;
    } else if (direccion != null) {
      map['direccion'] = direccion!.trim();
    }
    return map;
  }

  bool get hasChanges =>
      nombre != null ||
      apellido != null ||
      telefono != null ||
      direccion != null ||
      clearTelefono ||
      clearDireccion;
}
