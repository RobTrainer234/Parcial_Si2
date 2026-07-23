import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/client_service_history_model.dart';
import '../models/maintenance_appointment_model.dart';

final clientHistoryRepositoryProvider = Provider<ClientHistoryRepository>((ref) {
  return ClientHistoryRepository(ref.watch(apiClientProvider));
});

class ClientHistoryRepository {
  ClientHistoryRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<ClientServiceHistoryModel>> getServiceHistory() async {
    final response = await _apiClient.get('/client/services/history');
    return (response as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(ClientServiceHistoryModel.fromJson)
        .toList();
  }

  Future<List<MaintenanceAppointmentModel>> getAppointments() async {
    final response = await _apiClient.get('/client/maintenance-appointments');
    return (response as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(MaintenanceAppointmentModel.fromJson)
        .toList();
  }

  Future<List<MaintenanceWorkshopOptionModel>> getMaintenanceWorkshops() async {
    final response = await _apiClient.get('/client/maintenance-workshops');
    return (response as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(MaintenanceWorkshopOptionModel.fromJson)
        .toList();
  }

  Future<MaintenanceAppointmentModel> createAppointment({
    required int vehicleId,
    required int workshopId,
    required DateTime scheduledAt,
    String? reason,
  }) async {
    final response = await _apiClient.post(
      '/client/maintenance-appointments',
      data: {
        'vehicle_id': vehicleId,
        'workshop_id': workshopId,
        'scheduled_at': scheduledAt.toUtc().toIso8601String(),
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
      },
    );
    return MaintenanceAppointmentModel.fromJson(response as Map<String, dynamic>);
  }

  Future<void> cancelAppointment(int appointmentId) async {
    await _apiClient.patch('/client/maintenance-appointments/$appointmentId/cancel');
  }
}
