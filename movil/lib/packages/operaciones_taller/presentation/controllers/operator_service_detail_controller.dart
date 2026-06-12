import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/realtime/realtime_service.dart';
import '../../data/models/operator_navigation_status_model.dart';
import '../../data/models/operator_progress_response_model.dart';
import '../../data/models/operator_service_detail_model.dart';
import '../../data/repositories/operator_services_repository.dart';

class OperatorServiceDetailViewModel {
  final OperatorServiceDetailModel detail;
  final OperatorProgressSnapshotModel? progress;
  final OperatorNavigationStatusModel? navigationStatus;

  const OperatorServiceDetailViewModel({
    required this.detail,
    required this.progress,
    required this.navigationStatus,
  });
}

final operatorServiceDetailProvider =
    StateNotifierProvider.family<
      OperatorServiceDetailController,
      AsyncValue<OperatorServiceDetailViewModel>,
      int
    >((ref, serviceId) {
      ref.watch(
        authControllerProvider.select((state) {
          final user = state.valueOrNull?.user;
          return user == null
              ? null
              : '${user.userId}:${user.actorContext.operarioId ?? user.personaId}';
        }),
      );
      final repository = ref.watch(operatorServicesRepositoryProvider);
      final controller = OperatorServiceDetailController(repository, serviceId);
      ref.listen(realtimeEventsProvider, (_, next) {
        next.whenData((event) {
          if (event.isNotification && event.serviceId == serviceId) {
            controller.refresh();
          }
        });
      });
      return controller;
    });

class OperatorServiceDetailController
    extends StateNotifier<AsyncValue<OperatorServiceDetailViewModel>> {
  OperatorServiceDetailController(this._repository, this._serviceId)
    : super(const AsyncValue.loading()) {
    load();
  }

  final OperatorServicesRepository _repository;
  final int _serviceId;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final detail = await _repository.getServiceDetail(_serviceId);
      final progress = await _tryLoadProgress();
      final navigationStatus = await _tryLoadNavigationStatus();
      state = AsyncValue.data(
        OperatorServiceDetailViewModel(
          detail: detail,
          progress: progress,
          navigationStatus: navigationStatus,
        ),
      );
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<OperatorProgressSnapshotModel?> _tryLoadProgress() async {
    try {
      return await _repository.getProgressSnapshot(_serviceId);
    } on ApiException catch (error) {
      if (error.statusCode == 409) {
        return null;
      }
      rethrow;
    }
  }

  Future<OperatorNavigationStatusModel?> _tryLoadNavigationStatus() async {
    try {
      return await _repository.getNavigationStatus(_serviceId);
    } on ApiException catch (error) {
      if (error.statusCode == 409) {
        return null;
      }
      rethrow;
    }
  }

  Future<void> refresh() async {
    await load();
  }

  Future<void> acknowledgeProfile() async {
    await _repository.acknowledgeStructuredProfile(_serviceId);
    await load();
  }

  Future<OperatorProgressResponseModel> startNavigation({
    required double latitud,
    required double longitud,
    double? accuracyMeters,
    double? speedMps,
  }) async {
    final response = await _repository.startNavigation(
      serviceId: _serviceId,
      latitud: latitud,
      longitud: longitud,
      accuracyMeters: accuracyMeters,
      speedMps: speedMps,
    );
    await load();
    return response;
  }

  Future<OperatorProgressResponseModel> updateLocation({
    required double latitud,
    required double longitud,
    double? accuracyMeters,
    double? heading,
    double? speedMps,
    DateTime? deviceTimestamp,
  }) async {
    final response = await _repository.updateLocation(
      serviceId: _serviceId,
      latitud: latitud,
      longitud: longitud,
      accuracyMeters: accuracyMeters,
      heading: heading,
      speedMps: speedMps,
      deviceTimestamp: deviceTimestamp,
    );
    await load();
    return response;
  }

  Future<OperatorProgressResponseModel> updateProgress({
    required String newState,
    String? observation,
  }) async {
    final response = await _repository.updateProgress(
      serviceId: _serviceId,
      newState: newState,
      observation: observation,
    );
    await load();
    return response;
  }

  Future<OperatorProgressResponseModel> completeRepair({
    required String actionPerformed,
    String? physicalDiagnosis,
    String? observations,
    String? recommendations,
  }) async {
    final response = await _repository.saveRepairReport(
      serviceId: _serviceId,
      actionPerformed: actionPerformed,
      physicalDiagnosis: physicalDiagnosis,
      observations: observations,
      recommendations: recommendations,
    );
    await load();
    return response;
  }
}
