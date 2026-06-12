import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../network/api_client.dart';
import 'device_token_service.dart';
import 'firebase_messaging_service.dart';

final deviceTokenServiceProvider = Provider<DeviceTokenService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return DeviceTokenService(apiClient);
});

final firebaseMessagingServiceProvider = Provider<FirebaseMessagingService>(
  (_) => FirebaseMessagingService.instance,
);

final registerDeviceTokenProvider = FutureProvider<void>((ref) async {
  final messaging = ref.read(firebaseMessagingServiceProvider);
  final tokenService = ref.read(deviceTokenServiceProvider);

  await messaging.initialize();
  final token = await messaging.getToken();

  if (token == null) {
    debugPrint('registerDeviceTokenProvider: no token available');
    return;
  }

  String platform;
  try {
    platform = defaultTargetPlatform == TargetPlatform.iOS ? 'IOS' : 'ANDROID';
  } catch (_) {
    platform = 'ANDROID';
  }

  await tokenService.registerToken(deviceToken: token, platform: platform);
});
