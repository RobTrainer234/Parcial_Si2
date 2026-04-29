import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_exception.dart';
import 'dio_provider.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  final dio = ref.watch(dioProvider);
  return ApiClient(dio);
});

class ApiClient {
  final Dio _dio;

  ApiClient(this._dio);

  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    bool requiresAuth = true,
  }) async {
    try {
      final response = await _dio.get(
        path,
        queryParameters: queryParameters,
        options: Options(extra: {'requiresAuth': requiresAuth}),
      );
      return response.data;
    } on DioException catch (e) {
      throw _extractException(e);
    }
  }

  Future<dynamic> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    bool requiresAuth = true,
  }) async {
    try {
      final response = await _dio.post(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(extra: {'requiresAuth': requiresAuth}),
      );
      return response.data;
    } on DioException catch (e) {
      throw _extractException(e);
    }
  }

  Future<dynamic> patch(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    bool requiresAuth = true,
  }) async {
    try {
      final response = await _dio.patch(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(extra: {'requiresAuth': requiresAuth}),
      );
      return response.data;
    } on DioException catch (e) {
      throw _extractException(e);
    }
  }

  Future<dynamic> put(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    bool requiresAuth = true,
  }) async {
    try {
      final response = await _dio.put(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(extra: {'requiresAuth': requiresAuth}),
      );
      return response.data;
    } on DioException catch (e) {
      throw _extractException(e);
    }
  }

  Future<dynamic> delete(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    bool requiresAuth = true,
  }) async {
    try {
      final response = await _dio.delete(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(extra: {'requiresAuth': requiresAuth}),
      );
      return response.data;
    } on DioException catch (e) {
      throw _extractException(e);
    }
  }

  ApiException _extractException(DioException e) {
    if (e.error is ApiException) {
      return e.error as ApiException;
    }
    return ApiException(
      statusCode: e.response?.statusCode,
      message: 'Ocurrió un error inesperado al procesar la solicitud.',
      details: e.response?.data,
    );
  }
}
