import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/profile_me_model.dart';
import '../../data/models/profile_update_request_model.dart';
import '../../data/models/vehicle_upsert_request_model.dart';
import '../../data/repositories/profile_repository.dart';

final profileControllerProvider =
    StateNotifierProvider<ProfileController, AsyncValue<ProfileMeModel>>(
  (ref) {
    final repository = ref.watch(profileRepositoryProvider);
    return ProfileController(repository);
  },
);

class ProfileController extends StateNotifier<AsyncValue<ProfileMeModel>> {
  final ProfileRepository _repository;

  ProfileController(this._repository) : super(const AsyncValue.loading()) {
    loadProfile();
  }

  Future<void> loadProfile() async {
    state = const AsyncValue.loading();
    try {
      final profile = await _repository.getProfile();
      state = AsyncValue.data(profile);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> refresh() async {
    await loadProfile();
  }

  Future<void> updateProfile(ProfileUpdateRequestModel request) async {
    final updated = await _repository.updateProfile(request);
    state = AsyncValue.data(updated);
  }

  Future<void> createVehicle(VehicleUpsertRequestModel request) async {
    await _repository.createVehicle(request);
    await loadProfile();
  }

  Future<void> updateVehicle(
    int vehicleId,
    Map<String, dynamic> patch,
  ) async {
    await _repository.updateVehicle(vehicleId, patch);
    await loadProfile();
  }

  Future<void> deleteVehicle(int vehicleId) async {
    await _repository.deleteVehicle(vehicleId);
    await loadProfile();
  }
}
