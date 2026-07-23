class ClientServiceHistoryModel {
  const ClientServiceHistoryModel({
    required this.serviceId,
    required this.serviceState,
    required this.vehicleLabel,
    required this.workshopName,
    required this.createdAt,
    this.finalAmount,
    this.paymentStatus,
    this.rating,
    this.completedAt,
  });

  final int serviceId;
  final String serviceState;
  final String vehicleLabel;
  final String workshopName;
  final DateTime createdAt;
  final double? finalAmount;
  final String? paymentStatus;
  final int? rating;
  final DateTime? completedAt;

  factory ClientServiceHistoryModel.fromJson(Map<String, dynamic> json) {
    return ClientServiceHistoryModel(
      serviceId: (json['service_id'] as num).toInt(),
      serviceState: json['service_state'] as String? ?? '',
      vehicleLabel: json['vehicle_label'] as String? ?? 'Vehículo',
      workshopName: json['workshop_name'] as String? ?? 'Taller',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      finalAmount: (json['final_amount'] as num?)?.toDouble(),
      paymentStatus: json['payment_status'] as String?,
      rating: (json['rating'] as num?)?.toInt(),
      completedAt: json['completed_at'] == null
          ? null
          : DateTime.tryParse(json['completed_at'] as String),
    );
  }
}
