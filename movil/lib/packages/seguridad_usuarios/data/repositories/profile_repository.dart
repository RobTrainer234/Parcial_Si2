import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/profile_me_model.dart';
import '../models/profile_update_request_model.dart';
import '../models/vehicle_model.dart';
import '../models/vehicle_upsert_request_model.dart';

final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ProfileRepository(apiClient);
});

class ProfileRepository {
  final ApiClient _apiClient;

  ProfileRepository(this._apiClient);

  Future<ProfileMeModel> getProfile() async {
    final response = await _apiClient.get('/profile/me');
    return ProfileMeModel.fromJson(response as Map<String, dynamic>);
  }

  Future<ProfileMeModel> updateProfile(ProfileUpdateRequestModel request) async {
    final response = await _apiClient.patch(
      '/profile/me',
      data: request.toJson(),
    );
    return ProfileMeModel.fromJson(response as Map<String, dynamic>);
  }

  Future<List<VehicleModel>> getVehicles() async {
    final response = await _apiClient.get('/profile/me/vehicles');
    return (response as List<dynamic>)
        .map((v) => VehicleModel.fromJson(v as Map<String, dynamic>))
        .toList();
  }

  Future<VehicleModel> createVehicle(VehicleUpsertRequestModel request) async {
    final response = await _apiClient.post(
      '/profile/me/vehicles',
      data: request.toJson(),
    );
    return VehicleModel.fromJson(response as Map<String, dynamic>);
  }

  Future<VehicleModel> updateVehicle(
    int vehicleId,
    Map<String, dynamic> patch,
  ) async {
    final response = await _apiClient.patch(
      '/profile/me/vehicles/$vehicleId',
      data: patch,
    );
    return VehicleModel.fromJson(response as Map<String, dynamic>);
  }

  Future<void> deleteVehicle(int vehicleId) async {
    await _apiClient.delete('/profile/me/vehicles/$vehicleId');
  }
}
