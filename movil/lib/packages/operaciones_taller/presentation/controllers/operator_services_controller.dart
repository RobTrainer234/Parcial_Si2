import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/operator_assigned_service_model.dart';
import '../../data/repositories/operator_services_repository.dart';

final operatorServicesProvider = StateNotifierProvider<
    OperatorServicesController, AsyncValue<List<OperatorAssignedServiceModel>>>(
  (ref) {
    final repository = ref.watch(operatorServicesRepositoryProvider);
    return OperatorServicesController(repository);
  },
);

class OperatorServicesController
    extends StateNotifier<AsyncValue<List<OperatorAssignedServiceModel>>> {
  OperatorServicesController(this._repository)
      : super(const AsyncValue.loading()) {
    load();
  }

  final OperatorServicesRepository _repository;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final services = await _repository.getAssignedServices();
      state = AsyncValue.data(services);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refresh() async {
    await load();
  }
}
