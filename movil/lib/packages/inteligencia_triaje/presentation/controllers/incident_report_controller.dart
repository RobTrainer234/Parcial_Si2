import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../../../core/network/api_exception.dart';
import '../../data/models/incident_report_response_model.dart';
import '../../data/models/offline_incident_queue_item.dart';
import '../../data/models/specialty_model.dart';
import '../../data/repositories/triage_repository.dart';
import '../../data/services/offline_incident_queue_service.dart';
import 'offline_incident_queue_controller.dart';

final specialtiesProvider =
    StateNotifierProvider<
      SpecialtiesController,
      AsyncValue<List<SpecialtyModel>>
    >((ref) {
      final repository = ref.watch(triageRepositoryProvider);
      return SpecialtiesController(repository);
    });

class SpecialtiesController
    extends StateNotifier<AsyncValue<List<SpecialtyModel>>> {
  final TriageRepository _repository;

  SpecialtiesController(this._repository) : super(const AsyncValue.loading()) {
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
    StateNotifierProvider<
      IncidentSubmitController,
      AsyncValue<IncidentSubmitResult?>
    >((ref) {
      final repository = ref.watch(triageRepositoryProvider);
      final queueService = ref.watch(offlineIncidentQueueServiceProvider);
      final clientPersonaId = ref
          .watch(authControllerProvider)
          .valueOrNull
          ?.user
          ?.personaId;
      return IncidentSubmitController(
        repository,
        queueService,
        ref,
        clientPersonaId: clientPersonaId,
      );
    });

class IncidentSubmitResult {
  final IncidentReportResponseModel? onlineResponse;
  final OfflineIncidentQueueItem? queuedIncident;

  const IncidentSubmitResult._({this.onlineResponse, this.queuedIncident});

  const IncidentSubmitResult.online(IncidentReportResponseModel response)
    : this._(onlineResponse: response);

  const IncidentSubmitResult.queued(OfflineIncidentQueueItem item)
    : this._(queuedIncident: item);

  bool get wasQueued => queuedIncident != null;
}

class IncidentSubmitController
    extends StateNotifier<AsyncValue<IncidentSubmitResult?>> {
  final TriageRepository _repository;
  final OfflineIncidentQueueService _queueService;
  final Ref _ref;
  final int? _clientPersonaId;

  IncidentSubmitController(
    this._repository,
    this._queueService,
    this._ref, {
    required int? clientPersonaId,
  }) : _clientPersonaId = clientPersonaId,
       super(const AsyncValue.data(null));

  Future<IncidentSubmitResult> submitIncident({
    required int vehicleId,
    required double latitud,
    required double longitud,
    required String descripcionCliente,
    required int specialtyId,
    required String specialtyLabel,
    List<XFile> images = const [],
    String? audioPath,
  }) async {
    state = const AsyncValue.loading();
    final localUuid = _queueService.generateLocalUuid();
    try {
      final result = await _repository.reportIncident(
        vehicleId: vehicleId,
        latitud: latitud,
        longitud: longitud,
        descripcionCliente: descripcionCliente,
        specialtyId: specialtyId,
        localUuid: localUuid,
        images: images,
        audioPath: audioPath,
      );
      final submitResult = IncidentSubmitResult.online(result);
      state = AsyncValue.data(submitResult);
      return submitResult;
    } catch (e, st) {
      if (e is ApiException && e.statusCode == null) {
        final clientPersonaId = _clientPersonaId;
        if (clientPersonaId == null) {
          state = AsyncValue.error(e, st);
          rethrow;
        }
        final queuedItem = await _queueService.enqueue(
          clientPersonaId: clientPersonaId,
          localUuid: localUuid,
          vehicleId: vehicleId,
          description: descripcionCliente,
          specialtyId: specialtyId,
          specialtyLabel: specialtyLabel,
          latitud: latitud,
          longitud: longitud,
          photoPaths: images.map((item) => item.path).toList(),
          audioPath: audioPath,
        );
        await _ref
            .read(offlineIncidentQueueControllerProvider.notifier)
            .refreshSilently();
        final submitResult = IncidentSubmitResult.queued(queuedItem);
        state = AsyncValue.data(submitResult);
        return submitResult;
      }
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }
}
