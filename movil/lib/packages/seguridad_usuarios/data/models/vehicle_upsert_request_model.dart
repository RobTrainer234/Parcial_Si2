class VehicleUpsertRequestModel {
  final String placa;
  final int anio;
  final String marcaNombre;
  final String modeloNombre;
  final String colorNombre;

  const VehicleUpsertRequestModel({
    required this.placa,
    required this.anio,
    required this.marcaNombre,
    required this.modeloNombre,
    required this.colorNombre,
  });

  Map<String, dynamic> toJson() => {
        'placa': placa.toUpperCase().trim(),
        'anio': anio,
        'marca_nombre': marcaNombre.trim(),
        'modelo_nombre': modeloNombre.trim(),
        'color_nombre': colorNombre.trim(),
      };
}
