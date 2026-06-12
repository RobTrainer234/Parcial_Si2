import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class TallerRepuestoModel {
  final int idTallerRepuesto;
  final int idTaller;
  final String nombre;
  final String? descripcion;
  final double precioUnitario;
  final bool activo;

  const TallerRepuestoModel({
    required this.idTallerRepuesto,
    required this.idTaller,
    required this.nombre,
    this.descripcion,
    required this.precioUnitario,
    required this.activo,
  });

  factory TallerRepuestoModel.fromJson(Map<String, dynamic> json) {
    return TallerRepuestoModel(
      idTallerRepuesto: parseRequiredInt(json['id_taller_repuesto'], field: 'id_taller_repuesto'),
      idTaller: parseRequiredInt(json['id_taller'], field: 'id_taller'),
      nombre: json['nombre'] as String? ?? '',
      descripcion: json['descripcion'] as String?,
      precioUnitario: parseDoubleOrZero(json['precio_unitario']),
      activo: json['activo'] as bool? ?? true,
    );
  }
}

class UsedSparePartSelection {
  final TallerRepuestoModel repuesto;
  int cantidad;

  UsedSparePartSelection({
    required this.repuesto,
    this.cantidad = 1,
  });

  double get subtotal => repuesto.precioUnitario * cantidad;
}
