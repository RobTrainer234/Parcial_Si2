class VehicleModel {
  final int idVehiculo;
  final String placa;
  final int anio;
  final String marcaNombre;
  final String modeloNombre;
  final String colorNombre;

  const VehicleModel({
    required this.idVehiculo,
    required this.placa,
    required this.anio,
    required this.marcaNombre,
    required this.modeloNombre,
    required this.colorNombre,
  });

  factory VehicleModel.fromJson(Map<String, dynamic> json) {
    return VehicleModel(
      idVehiculo: json['id_vehiculo'] as int,
      placa: json['placa'] as String,
      anio: json['anio'] as int,
      marcaNombre: json['marca_nombre'] as String,
      modeloNombre: json['modelo_nombre'] as String,
      colorNombre: json['color_nombre'] as String,
    );
  }
}
