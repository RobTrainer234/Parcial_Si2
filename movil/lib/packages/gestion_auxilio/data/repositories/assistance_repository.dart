import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/hire_workshop_response_model.dart';
import '../models/incident_recommendations_model.dart';

final assistanceRepositoryProvider = Provider<AssistanceRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AssistanceRepository(apiClient);
});

class AssistanceRepository {
  final ApiClient _apiClient;

  AssistanceRepository(this._apiClient);

  Future<IncidentRecommendationsModel> getRecommendations(
      int incidentId) async {
    final response = await _apiClient
        .get('/assistance/incidents/$incidentId/recommendations');
    return IncidentRecommendationsModel.fromJson(
        response as Map<String, dynamic>);
  }

  Future<HireWorkshopResponseModel> hireWorkshop({
    required int incidentId,
    required int workshopId,
  }) async {
    final response = await _apiClient.post(
      '/assistance/incidents/$incidentId/hire',
      data: {'workshop_id': workshopId},
    );
    return HireWorkshopResponseModel.fromJson(
        response as Map<String, dynamic>);
  }
}
