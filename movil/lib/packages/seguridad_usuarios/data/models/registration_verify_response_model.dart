class RegistrationVerifyResponseModel {
  final String status;
  final String role;
  final String homeHint;
  final int? createdVehicleCount;

  const RegistrationVerifyResponseModel({
    required this.status,
    required this.role,
    required this.homeHint,
    this.createdVehicleCount,
  });

  factory RegistrationVerifyResponseModel.fromJson(Map<String, dynamic> json) {
    return RegistrationVerifyResponseModel(
      status: json['status'] as String,
      role: json['role'] as String,
      homeHint: json['home_hint'] as String? ?? '',
      createdVehicleCount: json['created_vehicle_count'] as int?,
    );
  }
}
