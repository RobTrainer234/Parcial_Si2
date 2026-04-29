import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/rating_response_model.dart';
import '../../data/models/rating_status_model.dart';
import '../../data/repositories/ratings_repository.dart';

final ratingControllerProvider = StateNotifierProvider.family<
    RatingController,
    AsyncValue<RatingStatusModel>,
    int>((ref, serviceId) {
  final repository = ref.watch(ratingsRepositoryProvider);
  return RatingController(repository, serviceId);
});

class RatingController extends StateNotifier<AsyncValue<RatingStatusModel>> {
  RatingController(this._repository, this._serviceId)
      : super(const AsyncValue.loading()) {
    loadStatus();
  }

  final RatingsRepository _repository;
  final int _serviceId;

  Future<void> loadStatus() async {
    state = const AsyncValue.loading();
    try {
      final value = await _repository.getRatingStatus(_serviceId);
      state = AsyncValue.data(value);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refresh() async {
    await loadStatus();
  }

  Future<RatingResponseModel> submitRating({
    required String targetType,
    required int? targetId,
    required int stars,
    String? comment,
  }) async {
    final response = await _repository.submitRating(
      serviceId: _serviceId,
      targetType: targetType,
      targetId: targetId,
      stars: stars,
      comment: comment,
    );
    await loadStatus();
    return response;
  }
}
