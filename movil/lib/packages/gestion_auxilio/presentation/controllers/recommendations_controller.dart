import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/hire_workshop_response_model.dart';
import '../../data/models/incident_recommendations_model.dart';
import '../../data/repositories/assistance_repository.dart';

final recommendationsProvider = StateNotifierProvider.family<
    RecommendationsController,
    AsyncValue<IncidentRecommendationsModel>,
    int>(
  (ref, incidentId) {
    final repository = ref.watch(assistanceRepositoryProvider);
    return RecommendationsController(repository, incidentId);
  },
);

class RecommendationsController
    extends StateNotifier<AsyncValue<IncidentRecommendationsModel>> {
  RecommendationsController(this._repository, this._incidentId)
      : super(const AsyncValue.loading()) {
    loadRecommendations(_incidentId);
  }

  final AssistanceRepository _repository;
  final int _incidentId;

  Future<void> loadRecommendations(int incidentId) async {
    state = const AsyncValue.loading();
    try {
      final data = await _repository.getRecommendations(incidentId);
      state = AsyncValue.data(data);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> load() async {
    await loadRecommendations(_incidentId);
  }

  Future<HireWorkshopResponseModel> hireWorkshop(int workshopId) async {
    return _repository.hireWorkshop(
      incidentId: _incidentId,
      workshopId: workshopId,
    );
  }
}
