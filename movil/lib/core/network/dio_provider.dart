import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../storage/secure_storage_service.dart';
import 'api_exception.dart';

final dioProvider = Provider<Dio>((ref) {
  final tokenStorage = ref.watch(tokenStorageProvider);
  
  final dio = Dio(
    BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
      sendTimeout: const Duration(seconds: 15),
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Only attach token to our backend requests
        if (options.path.startsWith('/') || options.path.startsWith(AppConfig.apiBaseUrl)) {
          final token = await tokenStorage.readAccessToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        }
        return handler.next(options);
      },
      onError: (DioException e, handler) {
        String message = 'Ocurrió un error inesperado al conectar con el servidor.';
        int? statusCode = e.response?.statusCode;
        dynamic details = e.response?.data;

        if (e.type == DioExceptionType.connectionTimeout ||
            e.type == DioExceptionType.sendTimeout ||
            e.type == DioExceptionType.receiveTimeout ||
            e.type == DioExceptionType.connectionError) {
          message = 'No se pudo conectar con el servidor. Revisa tu conexión a internet.';
        } else if (statusCode != null) {
          switch (statusCode) {
            case 400:
              message = 'Solicitud no válida. Revisa los datos enviados.';
              break;
            case 401:
              message = 'Credenciales incorrectas o sesión expirada.';
              break;
            case 403:
              message = 'No tienes permiso para realizar esta acción.';
              break;
            case 409:
              message = 'Conflicto en la operación. Los datos pueden estar duplicados.';
              break;
            case 422:
              message = 'Faltan datos obligatorios o su formato es incorrecto.';
              break;
            case 423:
              message = 'Acceso temporalmente bloqueado. Inténtalo más tarde.';
              break;
            default:
              if (statusCode >= 500) {
                message = 'Error en el servidor. Estamos trabajando para solucionarlo.';
              }
          }
        }

        final apiException = ApiException(
          statusCode: statusCode,
          message: message,
          details: details,
        );

        return handler.reject(
          DioException(
            requestOptions: e.requestOptions,
            response: e.response,
            type: e.type,
            error: apiException,
            message: apiException.message,
          ),
        );
      },
    ),
  );

  return dio;
});
