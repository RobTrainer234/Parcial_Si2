import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/network/dio_provider.dart';
import '../models/incident_classification_model.dart';
import '../models/incident_detail_model.dart';
import '../models/incident_report_response_model.dart';
import '../models/matchmaking_selection_model.dart';
import '../models/matchmaking_status_model.dart';
import '../models/specialty_model.dart';

final triageRepositoryProvider = Provider<TriageRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final dio = ref.watch(dioProvider);
  return TriageRepository(apiClient, dio);
});

class TriageRepository {
  final ApiClient _apiClient;
  final Dio _dio;

  TriageRepository(this._apiClient, this._dio);

  Future<List<SpecialtyModel>> getSpecialties() async {
    final response = await _apiClient.get('/triage/specialties');
    final items = <SpecialtyModel>[];
    for (final item in response as List<dynamic>) {
      if (item is! Map<String, dynamic>) continue;
      try {
        items.add(SpecialtyModel.fromJson(item));
      } on FormatException {
        continue;
      }
    }
    return items;
  }

  Future<IncidentReportResponseModel> reportIncident({
    required int vehicleId,
    required double latitud,
    required double longitud,
    required String descripcionCliente,
    required int specialtyId,
    List<XFile> images = const [],
    String? audioPath,
  }) async {
    final formData = FormData.fromMap({
      'id_vehiculo': vehicleId,
      'latitud': latitud.toString(),
      'longitud': longitud.toString(),
      'descripcion_cliente': descripcionCliente,
      'id_especialidad_reportada_cliente': specialtyId,
    });

    for (final image in images.take(5)) {
      final bytes = await image.readAsBytes();
      formData.files.add(
        MapEntry(
          'images',
          MultipartFile.fromBytes(
            bytes,
            filename: image.name,
            contentType: _imageContentType(image),
          ),
        ),
      );
    }
    if (audioPath != null && audioPath.trim().isNotEmpty) {
      formData.files.add(
        MapEntry(
          'audio',
          await MultipartFile.fromFile(
            audioPath,
            filename: _fileNameFromPath(audioPath),
            contentType: _mediaTypeFromPath(audioPath),
          ),
        ),
      );
    }

    try {
      final response = await _dio.post(
        '/triage/incidents/report',
        data: formData,
        options: Options(extra: {'requiresAuth': true}),
      );
      return IncidentReportResponseModel.fromJson(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      throw _mapDioException(e);
    }
  }

  Future<IncidentDetailModel> getIncidentDetail(int incidentId) async {
    final response = await _apiClient.get('/triage/incidents/$incidentId');
    return IncidentDetailModel.fromJson(response as Map<String, dynamic>);
  }

  Future<IncidentClassificationModel> classifyIncident(int incidentId) async {
    final response = await _apiClient.post(
      '/triage/incidents/$incidentId/classify',
    );
    return IncidentClassificationModel.fromJson(
      response as Map<String, dynamic>,
    );
  }

  Future<MatchmakingSelectionModel> matchmakeIncident(int incidentId) async {
    final response = await _apiClient.post(
      '/triage/incidents/$incidentId/matchmake',
    );
    return MatchmakingSelectionModel.fromJson(response as Map<String, dynamic>);
  }

  Future<MatchmakingStatusModel> getMatchmakingStatus(int incidentId) async {
    final response = await _apiClient.get(
      '/triage/incidents/$incidentId/matchmaking',
    );
    return MatchmakingStatusModel.fromJson(response as Map<String, dynamic>);
  }

  ApiException _mapDioException(DioException e) {
    if (e.error is ApiException) {
      return e.error as ApiException;
    }
    String message;
    final statusCode = e.response?.statusCode;
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.connectionError) {
      message =
          'No se pudo conectar con el servidor. Revisa tu conexión a internet.';
    } else if (statusCode != null && statusCode >= 500) {
      message = 'Error en el servidor. Intenta más tarde.';
    } else {
      message = 'Ocurrió un error inesperado.';
    }
    return ApiException(
      statusCode: statusCode,
      message: message,
      details: e.response?.data,
    );
  }
}

DioMediaType? _imageContentType(XFile image) {
  final explicitMimeType = image.mimeType?.trim();
  if (explicitMimeType != null && explicitMimeType.contains('/')) {
    try {
      return DioMediaType.parse(explicitMimeType);
    } on FormatException {
      // Fall back to filename inference below.
    }
  }
  return MultipartFile.lookupMediaType(image.name);
}

String _fileNameFromPath(String path) {
  final normalized = path.replaceAll('\\', '/');
  final segments = normalized.split('/');
  return segments.isEmpty ? 'audio.m4a' : segments.last;
}

DioMediaType? _mediaTypeFromPath(String path) {
  return MultipartFile.lookupMediaType(_fileNameFromPath(path));
}
