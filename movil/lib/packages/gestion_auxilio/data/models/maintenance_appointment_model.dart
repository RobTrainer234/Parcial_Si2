class MaintenanceAppointmentModel {
  const MaintenanceAppointmentModel({
    required this.appointmentId,
    required this.status,
    required this.scheduledAt,
    required this.vehicleId,
    required this.vehicleLabel,
    required this.workshopId,
    required this.workshopName,
    this.reason,
    this.clientNotes,
    this.workshopNotes,
    this.catalogServiceId,
    this.catalogServiceName,
  });

  final int appointmentId;
  final String status;
  final DateTime scheduledAt;
  final int vehicleId;
  final String vehicleLabel;
  final int workshopId;
  final String workshopName;
  final String? reason;
  final String? clientNotes;
  final String? workshopNotes;
  final int? catalogServiceId;
  final String? catalogServiceName;

  factory MaintenanceAppointmentModel.fromJson(Map<String, dynamic> json) {
    return MaintenanceAppointmentModel(
      appointmentId: (json['appointment_id'] as num).toInt(),
      status: json['status'] as String? ?? 'PENDIENTE',
      scheduledAt: DateTime.tryParse(json['scheduled_at'] as String? ?? '') ?? DateTime.now(),
      vehicleId: (json['vehicle_id'] as num).toInt(),
      vehicleLabel: json['vehicle_label'] as String? ?? 'Vehículo',
      workshopId: (json['workshop_id'] as num).toInt(),
      workshopName: json['workshop_name'] as String? ?? 'Taller',
      reason: json['reason'] as String?,
      clientNotes: json['client_notes'] as String?,
      workshopNotes: json['workshop_notes'] as String?,
      catalogServiceId: (json['catalog_service_id'] as num?)?.toInt(),
      catalogServiceName: json['catalog_service_name'] as String?,
    );
  }
}

class MaintenanceWorkshopOptionModel {
  const MaintenanceWorkshopOptionModel({
    required this.workshopId,
    required this.workshopName,
    this.city,
  });

  final int workshopId;
  final String workshopName;
  final String? city;

  factory MaintenanceWorkshopOptionModel.fromJson(Map<String, dynamic> json) {
    return MaintenanceWorkshopOptionModel(
      workshopId: (json['workshop_id'] as num).toInt(),
      workshopName: json['workshop_name'] as String? ?? 'Taller',
      city: json['city'] as String?,
    );
  }
}
