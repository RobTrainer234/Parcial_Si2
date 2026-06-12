import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../data/models/offline_incident_queue_item.dart';
import '../../data/services/offline_incident_queue_service.dart';

final offlineIncidentQueueControllerProvider =
    StateNotifierProvider<
      OfflineIncidentQueueController,
      AsyncValue<List<OfflineIncidentQueueItem>>
    >((ref) {
      final service = ref.watch(offlineIncidentQueueServiceProvider);
      final clientPersonaId = ref
          .watch(authControllerProvider)
          .valueOrNull
          ?.user
          ?.personaId;
      return OfflineIncidentQueueController(
        service,
        clientPersonaId: clientPersonaId,
      );
    });

final offlinePendingIncidentCountProvider = Provider<int>((ref) {
  final state = ref.watch(offlineIncidentQueueControllerProvider);
  final items = state.valueOrNull ?? const <OfflineIncidentQueueItem>[];
  return items
      .where((item) => item.status != OfflineIncidentSyncStatus.sincronizado)
      .length;
});

class OfflineIncidentQueueController
    extends StateNotifier<AsyncValue<List<OfflineIncidentQueueItem>>> {
  final OfflineIncidentQueueService _service;
  final int? _clientPersonaId;

  bool _syncInFlight = false;

  OfflineIncidentQueueController(this._service, {required int? clientPersonaId})
    : _clientPersonaId = clientPersonaId,
      super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    try {
      final items = await _service.getQueue(clientPersonaId: _clientPersonaId);
      state = AsyncValue.data(items);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refreshSilently() async {
    await load();
  }

  Future<void> syncPending({bool silent = false}) async {
    if (_syncInFlight) return;
    _syncInFlight = true;
    final previousState = state;
    if (!silent) {
      state = const AsyncValue.loading();
    }
    try {
      final items = await _service.syncPending(
        clientPersonaId: _clientPersonaId,
      );
      state = AsyncValue.data(items);
    } catch (error, stackTrace) {
      state = silent ? previousState : AsyncValue.error(error, stackTrace);
    } finally {
      _syncInFlight = false;
    }
  }
}
