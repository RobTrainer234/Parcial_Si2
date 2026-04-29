class VehicleRegistrationModel {
  final String placa;
  final int anio;
  final String marcaNombre;
  final String modeloNombre;
  final String colorNombre;

  const VehicleRegistrationModel({
    required this.placa,
    required this.anio,
    required this.marcaNombre,
    required this.modeloNombre,
    required this.colorNombre,
  });

  Map<String, dynamic> toJson() => {
        'placa': placa,
        'anio': anio,
        'marca_nombre': marcaNombre,
        'modelo_nombre': modeloNombre,
        'color_nombre': colorNombre,
      };
}
