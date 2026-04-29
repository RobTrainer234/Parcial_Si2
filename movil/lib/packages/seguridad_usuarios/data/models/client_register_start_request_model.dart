import 'vehicle_registration_model.dart';

class ClientRegisterStartRequestModel {
  final String nombre;
  final String apellido;
  final String ci;
  final String telefono;
  final String? direccion;
  final String email;
  final String password;
  final List<VehicleRegistrationModel> vehicles;

  const ClientRegisterStartRequestModel({
    required this.nombre,
    required this.apellido,
    required this.ci,
    required this.telefono,
    this.direccion,
    required this.email,
    required this.password,
    required this.vehicles,
  });

  Map<String, dynamic> toJson() => {
    'nombre': nombre,
    'apellido': apellido,
    'ci': ci,
    'telefono': telefono,
    'direccion': direccion,
    'email': email,
    'password': password,
    'vehicles': vehicles.map((v) => v.toJson()).toList(),
  };
}
