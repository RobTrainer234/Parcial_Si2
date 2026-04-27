class AppConfig {
  /// Base URL of the backend API.
  /// Android emulator: http://10.0.2.2:8000
  /// Windows desktop: http://127.0.0.1:8000
  /// Physical phone: http://[PC_LAN_IP]:8000
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
}
