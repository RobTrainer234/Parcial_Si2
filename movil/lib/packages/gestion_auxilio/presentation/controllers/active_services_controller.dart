import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/client_active_service_model.dart';
import '../../data/repositories/client_services_repository.dart';

final activeServicesProvider = StateNotifierProvider<ActiveServicesController,
    AsyncValue<List<ClientActiveServiceModel>>>((ref) {
  final repository = ref.watch(clientServicesRepositoryProvider);
  return ActiveServicesController(repository);
});

class ActiveServicesController
    extends StateNotifier<AsyncValue<List<ClientActiveServiceModel>>> {
  ActiveServicesController(this._repository) : super(const AsyncValue.loading()) {
    load();
  }

  final ClientServicesRepository _repository;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final items = await _repository.getActiveServices();
      state = AsyncValue.data(items);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refresh() async {
    await load();
  }
}
