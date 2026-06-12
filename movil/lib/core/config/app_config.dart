import 'package:flutter/foundation.dart';

class AppConfig {
  static const String _defaultWebApiBaseUrl = 'http://localhost/api';
  static const String _defaultMobileApiBaseUrl =
      'https://parcial-si2.onrender.com';

  /// Base URL of the backend API.
  /// Web local with Docker/Nginx: http://localhost/api
  /// Android/iOS fallback: https://parcial-si2.onrender.com
  static const String _rawApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  static String get apiBaseUrl {
    final trimmed = _rawApiBaseUrl.trim();
    if (trimmed.isEmpty) {
      return kIsWeb ? _defaultWebApiBaseUrl : _defaultMobileApiBaseUrl;
    }
    return trimmed.endsWith('/')
        ? trimmed.substring(0, trimmed.length - 1)
        : trimmed;
  }

  static Uri buildWebSocketUri(
    String path, {
    Map<String, String>? queryParameters,
  }) {
    final base = Uri.parse(apiBaseUrl);
    final scheme = base.scheme == 'https' ? 'wss' : 'ws';
    final baseSegments = base.pathSegments
        .where((segment) => segment.isNotEmpty)
        .toList();
    if (baseSegments.isNotEmpty && baseSegments.last.toLowerCase() == 'api') {
      baseSegments.removeLast();
    }
    final targetSegments = [
      ...baseSegments,
      ...path.split('/').where((segment) => segment.isNotEmpty),
    ];
    return base.replace(
      scheme: scheme,
      pathSegments: targetSegments,
      queryParameters: queryParameters,
    );
  }

  static String get realtimeWebSocketUrl {
    final apiUri = Uri.parse(apiBaseUrl);
    return apiUri
        .replace(
          scheme: apiUri.scheme == 'https' ? 'wss' : 'ws',
          path:
              '${apiUri.path.replaceAll(RegExp(r'/+$'), '').replaceAll(RegExp(r'/api$'), '')}/realtime/ws',
        )
        .toString();
  }
}
