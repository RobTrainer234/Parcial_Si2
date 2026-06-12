import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/incident_classification_model.dart';
import '../../data/models/incident_detail_model.dart';
import '../../data/repositories/triage_repository.dart';

final incidentDiagnosisProvider =
    StateNotifierProvider.family<
      IncidentDiagnosisController,
      AsyncValue<IncidentDetailModel>,
      int
    >((ref, incidentId) {
      final repository = ref.watch(triageRepositoryProvider);
      return IncidentDiagnosisController(repository, incidentId);
    });

class IncidentDiagnosisController
    extends StateNotifier<AsyncValue<IncidentDetailModel>> {
  IncidentDiagnosisController(this._repository, this._incidentId)
    : super(const AsyncValue.loading()) {
    loadIncidentDetail(_incidentId, classifyIfNeeded: true);
  }

  final TriageRepository _repository;
  final int _incidentId;

  IncidentClassificationModel? lastClassification;

  Future<void> loadIncidentDetail(
    int incidentId, {
    bool classifyIfNeeded = false,
  }) async {
    state = const AsyncValue.loading();
    try {
      final detail = await _repository.getIncidentDetail(incidentId);
      if (classifyIfNeeded && detail.needsClassification) {
        final classification = await _repository.classifyIncident(incidentId);
        lastClassification = classification;
        final refreshedDetail = await _repository.getIncidentDetail(incidentId);
        state = AsyncValue.data(refreshedDetail);
        return;
      }
      state = AsyncValue.data(detail);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<IncidentClassificationModel> runDiagnosis(int incidentId) async {
    final classification = await _repository.classifyIncident(incidentId);
    lastClassification = classification;
    final detail = await _repository.getIncidentDetail(incidentId);
    state = AsyncValue.data(detail);
    return classification;
  }

  Future<void> refresh(int incidentId) async {
    await loadIncidentDetail(incidentId, classifyIfNeeded: true);
  }
}
