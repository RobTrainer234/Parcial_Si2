import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/rating_response_model.dart';
import '../models/rating_status_model.dart';

final ratingsRepositoryProvider = Provider<RatingsRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return RatingsRepository(apiClient);
});

class RatingsRepository {
  RatingsRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<RatingStatusModel> getRatingStatus(int serviceId) async {
    final response =
        await _apiClient.get('/reputation/services/$serviceId/rating-status');
    return RatingStatusModel.fromJson(response as Map<String, dynamic>);
  }

  Future<RatingResponseModel> submitRating({
    required int serviceId,
    required String targetType,
    required int? targetId,
    required int stars,
    String? comment,
  }) async {
    final payload = <String, dynamic>{
      'target_type': targetType,
      'target_id': targetId,
      'estrellas': stars,
      if (comment != null && comment.trim().isNotEmpty)
        'comentario': comment.trim(),
    };
    final response = await _apiClient.post(
      '/reputation/services/$serviceId/rating',
      data: payload,
    );
    return RatingResponseModel.fromJson(response as Map<String, dynamic>);
  }
}
