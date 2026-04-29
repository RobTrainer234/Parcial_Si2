import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/client_active_service_model.dart';
import '../models/finalization_decision_response_model.dart';
import '../models/finalization_status_model.dart';
import '../models/service_prequotation_model.dart';
import '../models/tracking_history_point_model.dart';
import '../models/tracking_status_model.dart';

final clientServicesRepositoryProvider = Provider<ClientServicesRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ClientServicesRepository(apiClient);
});

class ClientServicesRepository {
  ClientServicesRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<ClientActiveServiceModel>> getActiveServices() async {
    final response = await _apiClient.get('/client/services/active');
    return (response as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(ClientActiveServiceModel.fromJson)
        .toList();
  }

  Future<TrackingStatusModel> getTrackingStatus(int serviceId) async {
    final response = await _apiClient.get('/tracking/services/$serviceId/status');
    return TrackingStatusModel.fromJson(response as Map<String, dynamic>);
  }

  Future<List<TrackingHistoryPointModel>> getTrackingHistory(int serviceId) async {
    final response = await _apiClient.get('/tracking/services/$serviceId/history');
    return (response as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(TrackingHistoryPointModel.fromJson)
        .toList();
  }

  Future<ServicePrequotationModel> getPrequotation(int serviceId) async {
    final response =
        await _apiClient.get('/client/services/$serviceId/prequotation');
    return ServicePrequotationModel.fromJson(response as Map<String, dynamic>);
  }

  Future<FinalizationStatusModel> getFinalizationStatus(int serviceId) async {
    final response =
        await _apiClient.get('/field/services/$serviceId/finalization-status');
    return FinalizationStatusModel.fromJson(response as Map<String, dynamic>);
  }

  Future<FinalizationDecisionResponseModel> decideFinalization({
    required int serviceId,
    required String decision,
    String? motivo,
  }) async {
    final payload = <String, dynamic>{
      'decision': decision,
      if (motivo != null && motivo.trim().isNotEmpty) 'motivo': motivo.trim(),
    };
    final response = await _apiClient.post(
      '/client/services/$serviceId/finalization/decision',
      data: payload,
    );
    return FinalizationDecisionResponseModel.fromJson(
      response as Map<String, dynamic>,
    );
  }
}
