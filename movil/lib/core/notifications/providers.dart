import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../network/api_client.dart';
import 'device_token_service.dart';

final deviceTokenServiceProvider = Provider<DeviceTokenService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return DeviceTokenService(apiClient);
});
