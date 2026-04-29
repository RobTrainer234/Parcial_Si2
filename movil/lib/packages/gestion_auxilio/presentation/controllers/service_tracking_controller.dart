import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/service_prequotation_model.dart';
import '../../data/models/tracking_history_point_model.dart';
import '../../data/models/tracking_status_model.dart';
import '../../data/repositories/client_services_repository.dart';

class ServiceTrackingViewModel {
  final TrackingStatusModel status;
  final List<TrackingHistoryPointModel> history;

  const ServiceTrackingViewModel({
    required this.status,
    required this.history,
  });
}

final serviceTrackingProvider = StateNotifierProvider.family<
    ServiceTrackingController,
    AsyncValue<ServiceTrackingViewModel>,
    int>((ref, serviceId) {
  final repository = ref.watch(clientServicesRepositoryProvider);
  return ServiceTrackingController(repository, serviceId);
});

final servicePrequotationProvider =
    FutureProvider.family<ServicePrequotationModel, int>((ref, serviceId) async {
  final repository = ref.watch(clientServicesRepositoryProvider);
  return repository.getPrequotation(serviceId);
});

class ServiceTrackingController
    extends StateNotifier<AsyncValue<ServiceTrackingViewModel>> {
  ServiceTrackingController(this._repository, this._serviceId)
      : super(const AsyncValue.loading()) {
    load();
  }

  final ClientServicesRepository _repository;
  final int _serviceId;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      state = AsyncValue.data(await _fetchViewModel());
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refresh() async {
    await load();
  }

  Future<void> refreshSilently() async {
    final previous = state.valueOrNull;
    try {
      final next = await _fetchViewModel();
      state = AsyncValue.data(next);
    } catch (error, stackTrace) {
      if (previous == null) {
        state = AsyncValue.error(error, stackTrace);
      }
    }
  }

  Future<ServiceTrackingViewModel> _fetchViewModel() async {
    final status = await _repository.getTrackingStatus(_serviceId);
    final history = await _repository.getTrackingHistory(_serviceId);
    return ServiceTrackingViewModel(
      status: status,
      history: history,
    );
  }
}
