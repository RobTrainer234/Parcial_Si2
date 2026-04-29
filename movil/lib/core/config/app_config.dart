class AppConfig {
  /// Base URL of the backend API.
  /// Docker/Nginx local or production-style: http://localhost/api
  /// Direct backend example: http://127.0.0.1:8000/api
  static const String _rawApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost/api',
  );

  static String get apiBaseUrl {
    final trimmed = _rawApiBaseUrl.trim();
    if (trimmed.isEmpty) {
      return 'http://localhost/api';
    }
    return trimmed.endsWith('/') ? trimmed.substring(0, trimmed.length - 1) : trimmed;
  }
}
