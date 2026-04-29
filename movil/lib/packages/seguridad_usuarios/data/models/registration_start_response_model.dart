class RegistrationStartResponseModel {
  final String status;
  final String role;
  final String registrationToken;
  final DateTime? expiresAt;
  final String? verificationCodeForTesting;

  const RegistrationStartResponseModel({
    required this.status,
    required this.role,
    required this.registrationToken,
    this.expiresAt,
    this.verificationCodeForTesting,
  });

  factory RegistrationStartResponseModel.fromJson(Map<String, dynamic> json) {
    return RegistrationStartResponseModel(
      status: json['status'] as String,
      role: json['role'] as String,
      registrationToken: json['registration_token'] as String,
      expiresAt: json['expires_at'] != null
          ? DateTime.tryParse(json['expires_at'] as String)
          : null,
      verificationCodeForTesting: json['debug_verification_code'] as String?,
    );
  }
}
