import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/operator_navigation_status_model.dart';
import '../models/operator_assigned_service_model.dart';
import '../models/operator_progress_response_model.dart';
import '../models/operator_service_detail_model.dart';

final operatorServicesRepositoryProvider =
    Provider<OperatorServicesRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return OperatorServicesRepository(apiClient);
});

class OperatorServicesRepository {
  OperatorServicesRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<OperatorAssignedServiceModel>> getAssignedServices() async {
    final response = await _apiClient.get('/triage/operario/services/assigned');
    return (response as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(OperatorAssignedServiceModel.fromJson)
        .toList();
  }

  Future<OperatorServiceDetailModel> getServiceDetail(int serviceId) async {
    final response = await _apiClient.get(
      '/triage/operario/services/$serviceId/structured-profile',
    );
    return OperatorServiceDetailModel.fromJson(response as Map<String, dynamic>);
  }

  Future<void> acknowledgeStructuredProfile(int serviceId) async {
    await _apiClient.post(
      '/triage/operario/services/$serviceId/structured-profile/acknowledge',
    );
  }

  Future<OperatorProgressSnapshotModel> getProgressSnapshot(int serviceId) async {
    final response = await _apiClient.get('/field/services/$serviceId/progress');
    return OperatorProgressSnapshotModel.fromJson(
      response as Map<String, dynamic>,
    );
  }

  Future<OperatorNavigationStatusModel> getNavigationStatus(int serviceId) async {
    final response = await _apiClient.get(
      '/field/services/$serviceId/navigation/status',
    );
    return OperatorNavigationStatusModel.fromJson(
      response as Map<String, dynamic>,
    );
  }

  Future<OperatorProgressResponseModel> startNavigation({
    required int serviceId,
    required double latitud,
    required double longitud,
    double? accuracyMeters,
    double? speedMps,
  }) async {
    final response = await _apiClient.post(
      '/field/services/$serviceId/navigation/start',
      data: {
        'latitud_actual': latitud,
        'longitud_actual': longitud,
        if (accuracyMeters != null) 'accuracy_meters': accuracyMeters,
        if (speedMps != null) 'speed_mps': speedMps,
      },
    );
    return OperatorProgressResponseModel.fromJson(
      response as Map<String, dynamic>,
    );
  }

  Future<OperatorProgressResponseModel> updateLocation({
    required int serviceId,
    required double latitud,
    required double longitud,
    double? accuracyMeters,
    double? heading,
    double? speedMps,
    DateTime? deviceTimestamp,
  }) async {
    final response = await _apiClient.post(
      '/field/services/$serviceId/location',
      data: {
        'latitud': latitud,
        'longitud': longitud,
        if (accuracyMeters != null) 'accuracy_meters': accuracyMeters,
        if (heading != null) 'heading': heading,
        if (speedMps != null) 'speed_mps': speedMps,
        if (deviceTimestamp != null)
          'device_timestamp': deviceTimestamp.toIso8601String(),
      },
    );
    return OperatorProgressResponseModel.fromJson(
      response as Map<String, dynamic>,
    );
  }

  Future<OperatorProgressResponseModel> updateProgress({
    required int serviceId,
    required String newState,
    String? observation,
  }) async {
    final response = await _apiClient.post(
      '/field/services/$serviceId/progress',
      data: {
        'new_state': newState,
        if (observation != null && observation.trim().isNotEmpty)
          'observacion': observation.trim(),
      },
    );
    return OperatorProgressResponseModel.fromJson(
      response as Map<String, dynamic>,
    );
  }

  Future<OperatorProgressResponseModel> saveRepairReport({
    required int serviceId,
    required String actionPerformed,
    String? physicalDiagnosis,
    String? observations,
    String? recommendations,
  }) async {
    final data = FormData.fromMap({
      'accion_realizada': actionPerformed,
      if (physicalDiagnosis != null && physicalDiagnosis.trim().isNotEmpty)
        'diagnostico_fisico': physicalDiagnosis.trim(),
      if (observations != null && observations.trim().isNotEmpty)
        'observaciones': observations.trim(),
      if (recommendations != null && recommendations.trim().isNotEmpty)
        'recomendaciones': recommendations.trim(),
      'used_items': '[]',
    });
    final response = await _apiClient.post(
      '/workshop/services/$serviceId/repair-report',
      data: data,
    );
    return OperatorProgressResponseModel.fromJson(
      response as Map<String, dynamic>,
    );
  }
}
