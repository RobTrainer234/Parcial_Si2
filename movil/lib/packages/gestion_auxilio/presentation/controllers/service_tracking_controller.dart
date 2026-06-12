import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/realtime/realtime_service.dart';
import '../../../../core/realtime/service_realtime_socket.dart';
import '../../data/models/service_prequotation_model.dart';
import '../../data/models/tracking_history_point_model.dart';
import '../../data/models/tracking_status_model.dart';
import '../../data/repositories/client_services_repository.dart';

class ServiceTrackingViewModel {
  final TrackingStatusModel status;
  final List<TrackingHistoryPointModel> history;

  const ServiceTrackingViewModel({
    required this.status,
    required this.history,
  });
}

final serviceTrackingProvider = StateNotifierProvider.family<
    ServiceTrackingController,
    AsyncValue<ServiceTrackingViewModel>,
    int>((ref, serviceId) {
  final repository = ref.watch(clientServicesRepositoryProvider);
  final controller = ServiceTrackingController(repository, serviceId);
  ref.listen(realtimeEventsProvider, (_, next) {
    next.whenData((event) {
      if (event.isNotification && event.serviceId == serviceId) {
        controller.refreshSilently();
      }
    });
  });
  return controller;
});

final servicePrequotationProvider =
    FutureProvider.family<ServicePrequotationModel, int>((ref, serviceId) async {
  final repository = ref.watch(clientServicesRepositoryProvider);
  return repository.getPrequotation(serviceId);
});

class ServiceTrackingController
    extends StateNotifier<AsyncValue<ServiceTrackingViewModel>> {
  ServiceTrackingController(this._repository, this._serviceId)
      : super(const AsyncValue.loading()) {
    load();
  }

  final ClientServicesRepository _repository;
  final int _serviceId;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      state = AsyncValue.data(await _fetchViewModel());
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refresh() async {
    await load();
  }

  Future<void> refreshSilently() async {
    final previous = state.valueOrNull;
    try {
      final next = await _fetchViewModel();
      state = AsyncValue.data(next);
    } catch (error, stackTrace) {
      if (previous == null) {
        state = AsyncValue.error(error, stackTrace);
      }
    }
  }

  void applyRealtimeEvent(ServiceRealtimeEvent event) {
    final previous = state.valueOrNull;
    if (previous == null || event.serviceId != _serviceId) {
      return;
    }

    final nextStatus = previous.status.copyWith(
      serviceState: event.serviceState ?? previous.status.serviceState,
      incidentId: event.incidentId ?? previous.status.incidentId,
      incidentLatitud:
          _asDouble(event.data['incident_latitud']) ??
          previous.status.incidentLatitud,
      incidentLongitud:
          _asDouble(event.data['incident_longitud']) ??
          previous.status.incidentLongitud,
      lastOperarioLatitud:
          _asDouble(event.data['operario_latitud']) ??
          previous.status.lastOperarioLatitud,
      lastOperarioLongitud:
          _asDouble(event.data['operario_longitud']) ??
          previous.status.lastOperarioLongitud,
      lastLocationAt:
          _asDate(event.data['last_location_at']) ??
          previous.status.lastLocationAt,
      hasLiveLocation:
          event.data['has_live_location'] as bool? ??
          previous.status.hasLiveLocation,
      locationStale:
          event.data['location_stale'] as bool? ?? previous.status.locationStale,
      currentDistanceMeters:
          _asDouble(event.data['current_distance_meters']) ??
          previous.status.currentDistanceMeters,
      etaSeconds:
          _asInt(event.data['eta_seconds']) ?? previous.status.etaSeconds,
      etaText: event.data['eta_text'] as String? ?? previous.status.etaText,
      routeDistanceMeters:
          _asDouble(event.data['route_distance_meters']) ??
          previous.status.routeDistanceMeters,
      routeDurationSeconds:
          _asDouble(event.data['route_duration_seconds']) ??
          previous.status.routeDurationSeconds,
      routePoints: TrackingStatusModel.fromJson({
            'service_id': previous.status.serviceId,
            'incident_id': previous.status.incidentId,
            'incident_latitud': previous.status.incidentLatitud,
            'incident_longitud': previous.status.incidentLongitud,
            'has_live_location': previous.status.hasLiveLocation,
            'location_stale': previous.status.locationStale,
            'tracking_message': previous.status.trackingMessage,
            'route_points': event.data['route_points'],
          }).routePoints ??
          previous.status.routePoints,
    );

    final nextHistory = List<TrackingHistoryPointModel>.from(previous.history);
    final lat = _asDouble(event.data['operario_latitud']);
    final lng = _asDouble(event.data['operario_longitud']);
    final at = _asDate(event.data['last_location_at']) ?? DateTime.now().toUtc();
    if (lat != null && lng != null) {
      final last = nextHistory.isNotEmpty ? nextHistory.last : null;
      final isDuplicate = last?.latitud == lat && last?.longitud == lng;
      if (!isDuplicate) {
        nextHistory.add(
          TrackingHistoryPointModel(
            latitud: lat,
            longitud: lng,
            fechaHora: at,
          ),
        );
      }
    }

    state = AsyncValue.data(
      ServiceTrackingViewModel(
        status: nextStatus,
        history: nextHistory,
      ),
    );
  }

  Future<ServiceTrackingViewModel> _fetchViewModel() async {
    final status = await _repository.getTrackingStatus(_serviceId);
    final history = await _repository.getTrackingHistory(_serviceId);
    return ServiceTrackingViewModel(
      status: status,
      history: history,
    );
  }
}

double? _asDouble(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}

int? _asInt(dynamic value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value);
  }
  return null;
}

DateTime? _asDate(dynamic value) {
  if (value is String && value.trim().isNotEmpty) {
    return DateTime.tryParse(value)?.toUtc();
  }
  return null;
}
