import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class PaymentMethodModel {
  final int idMetodoPago;
  final String nombre;
  final String? descripcion;
  final bool activo;

  const PaymentMethodModel({
    required this.idMetodoPago,
    required this.nombre,
    this.descripcion,
    required this.activo,
  });

  factory PaymentMethodModel.fromJson(Map<String, dynamic> json) {
    final id = parseNullableInt(json['id_metodo_pago']) ??
        parseNullableInt(json['id_metodo']);
    if (id == null || id <= 0) {
      throw const FormatException('Invalid payment method id.');
    }

    return PaymentMethodModel(
      idMetodoPago: id,
      nombre: json['nombre'] as String? ?? '',
      descripcion: json['descripcion'] as String?,
      activo: json['activo'] as bool? ?? true,
    );
  }
}
