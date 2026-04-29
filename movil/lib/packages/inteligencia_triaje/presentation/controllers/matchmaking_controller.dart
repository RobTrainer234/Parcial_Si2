import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/matchmaking_selection_model.dart';
import '../../data/models/matchmaking_status_model.dart';
import '../../data/repositories/triage_repository.dart';

class MatchmakingViewModel {
  final MatchmakingSelectionModel? selection;
  final MatchmakingStatusModel? status;

  const MatchmakingViewModel({
    this.selection,
    this.status,
  });

  MatchmakingViewModel copyWith({
    MatchmakingSelectionModel? selection,
    MatchmakingStatusModel? status,
  }) {
    return MatchmakingViewModel(
      selection: selection ?? this.selection,
      status: status ?? this.status,
    );
  }
}

final matchmakingProvider = StateNotifierProvider.family<
    MatchmakingController,
    AsyncValue<MatchmakingViewModel>,
    int>(
  (ref, incidentId) {
    final repository = ref.watch(triageRepositoryProvider);
    return MatchmakingController(repository, incidentId);
  },
);

class MatchmakingController
    extends StateNotifier<AsyncValue<MatchmakingViewModel>> {
  MatchmakingController(this._repository, this._incidentId)
      : super(const AsyncValue.data(MatchmakingViewModel()));

  final TriageRepository _repository;
  final int _incidentId;

  Future<MatchmakingSelectionModel> startMatchmaking(int incidentId) async {
    final previousModel = state.valueOrNull;
    state = const AsyncValue.loading();
    try {
      final selection = await _repository.matchmakeIncident(incidentId);
      MatchmakingStatusModel? status;
      if (selection.requestId != null || selection.selectedWorkshop != null) {
        try {
          status = await _repository.getMatchmakingStatus(incidentId);
        } catch (_) {
          status = null;
        }
      }
      final model = MatchmakingViewModel(
        selection: selection,
        status: status ?? previousModel?.status,
      );
      state = AsyncValue.data(model);
      return selection;
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
      rethrow;
    }
  }

  Future<MatchmakingStatusModel> loadStatus(int incidentId) async {
    final previousModel = state.valueOrNull;
    state = const AsyncValue.loading();
    try {
      final status = await _repository.getMatchmakingStatus(incidentId);
      final model = MatchmakingViewModel(
        selection: previousModel?.selection,
        status: status,
      );
      state = AsyncValue.data(model);
      return status;
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
      rethrow;
    }
  }

  Future<void> refresh() async {
    await loadStatus(_incidentId);
  }
}
