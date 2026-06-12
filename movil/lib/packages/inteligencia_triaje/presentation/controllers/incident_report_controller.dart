import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../data/models/incident_report_response_model.dart';
import '../../data/models/specialty_model.dart';
import '../../data/repositories/triage_repository.dart';

final specialtiesProvider =
    StateNotifierProvider<SpecialtiesController, AsyncValue<List<SpecialtyModel>>>(
  (ref) {
    final repository = ref.watch(triageRepositoryProvider);
    return SpecialtiesController(repository);
  },
);

class SpecialtiesController
    extends StateNotifier<AsyncValue<List<SpecialtyModel>>> {
  final TriageRepository _repository;

  SpecialtiesController(this._repository)
      : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final specialties = await _repository.getSpecialties();
      state = AsyncValue.data(specialties);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}

final incidentSubmitProvider =
    StateNotifierProvider<IncidentSubmitController, AsyncValue<IncidentReportResponseModel?>>(
  (ref) {
    final repository = ref.watch(triageRepositoryProvider);
    return IncidentSubmitController(repository);
  },
);

class IncidentSubmitController
    extends StateNotifier<AsyncValue<IncidentReportResponseModel?>> {
  final TriageRepository _repository;

  IncidentSubmitController(this._repository)
      : super(const AsyncValue.data(null));

  Future<IncidentReportResponseModel> submitIncident({
    required int vehicleId,
    required double latitud,
    required double longitud,
    required String descripcionCliente,
    required int specialtyId,
    List<XFile> images = const [],
    String? audioPath,
  }) async {
    state = const AsyncValue.loading();
    try {
      final result = await _repository.reportIncident(
        vehicleId: vehicleId,
        latitud: latitud,
        longitud: longitud,
        descripcionCliente: descripcionCliente,
        specialtyId: specialtyId,
        images: images,
        audioPath: audioPath,
      );
      state = AsyncValue.data(result);
      return result;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }
}
