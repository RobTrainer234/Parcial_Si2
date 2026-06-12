import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/taller_repuesto_model.dart';

final sparePartsRepositoryProvider =
    Provider<SparePartsRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SparePartsRepository(apiClient);
});

class SparePartsRepository {
  SparePartsRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<TallerRepuestoModel>> list(bool onlyActive) async {
    final response = await _apiClient.get('/workshop/spare-parts', queryParameters: {
      'only_active': onlyActive.toString(),
    });
    return (response as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(TallerRepuestoModel.fromJson)
        .toList();
  }
}
