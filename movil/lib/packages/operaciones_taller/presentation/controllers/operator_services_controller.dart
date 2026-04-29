import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../data/models/operator_assigned_service_model.dart';
import '../../data/repositories/operator_services_repository.dart';

final operatorServicesProvider =
    StateNotifierProvider<
      OperatorServicesController,
      AsyncValue<List<OperatorAssignedServiceModel>>
    >((ref) {
      final repository = ref.watch(operatorServicesRepositoryProvider);
      final operarioIdentity = ref.watch(
        authControllerProvider.select((state) {
          final session = state.valueOrNull;
          if (session?.role != 'OPERARIO') {
            return null;
          }
          final user = session?.user;
          return user == null
              ? null
              : '${user.userId}:${user.actorContext.operarioId ?? user.personaId}';
        }),
      );
      return OperatorServicesController(
        repository,
        shouldLoad: operarioIdentity != null,
      );
    });

class OperatorServicesController
    extends StateNotifier<AsyncValue<List<OperatorAssignedServiceModel>>> {
  OperatorServicesController(this._repository, {required bool shouldLoad})
    : _shouldLoad = shouldLoad,
      super(const AsyncValue.loading()) {
    if (_shouldLoad) {
      load();
    }
  }

  final OperatorServicesRepository _repository;
  final bool _shouldLoad;

  Future<void> load() async {
    if (!_shouldLoad) {
      return;
    }
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
