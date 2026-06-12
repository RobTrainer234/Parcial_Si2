import 'package:flutter/foundation.dart';

import '../network/api_client.dart';

class DeviceTokenService {
  DeviceTokenService(this._apiClient);

  final ApiClient _apiClient;

  Future<bool> registerToken({
    required String deviceToken,
    required String platform,
  }) async {
    try {
      await _apiClient.post(
        '/notifications/devices/register',
        data: {
          'device_token': deviceToken,
          'platform': platform,
          'notifications_enabled': true,
        },
        requiresAuth: true,
      );
      debugPrint('DeviceTokenService: token registered successfully');
      return true;
    } catch (e) {
      debugPrint('DeviceTokenService: register failed ($e)');
      return false;
    }
  }

  Future<bool> unregisterToken(String deviceToken) async {
    try {
      await _apiClient.post(
        '/notifications/devices/unregister',
        data: {'device_token': deviceToken},
        requiresAuth: true,
      );
      debugPrint('DeviceTokenService: token unregistered successfully');
      return true;
    } catch (e) {
      debugPrint('DeviceTokenService: unregister failed ($e)');
      return false;
    }
  }
}
