import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/finalization_decision_response_model.dart';
import '../../data/models/finalization_status_model.dart';
import '../../data/repositories/client_services_repository.dart';

final serviceFinalizationProvider = StateNotifierProvider.family<
    ServiceFinalizationController,
    AsyncValue<FinalizationStatusModel>,
    int>((ref, serviceId) {
  final repository = ref.watch(clientServicesRepositoryProvider);
  return ServiceFinalizationController(repository, serviceId);
});

class ServiceFinalizationController
    extends StateNotifier<AsyncValue<FinalizationStatusModel>> {
  ServiceFinalizationController(this._repository, this._serviceId)
      : super(const AsyncValue.loading()) {
    load();
  }

  final ClientServicesRepository _repository;
  final int _serviceId;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final value = await _repository.getFinalizationStatus(_serviceId);
      state = AsyncValue.data(value);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refresh() async {
    await load();
  }

  Future<FinalizationDecisionResponseModel> confirm() async {
    final response = await _repository.decideFinalization(
      serviceId: _serviceId,
      decision: 'CONFIRMAR',
    );
    await load();
    return response;
  }

  Future<FinalizationDecisionResponseModel> reject(String motivo) async {
    final response = await _repository.decideFinalization(
      serviceId: _serviceId,
      decision: 'RECHAZAR',
      motivo: motivo,
    );
    await load();
    return response;
  }
}
