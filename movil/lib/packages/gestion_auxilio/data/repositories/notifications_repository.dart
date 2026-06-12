import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/notification_item_model.dart';
import '../models/unread_count_model.dart';

final notificationsRepositoryProvider = Provider<NotificationsRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return NotificationsRepository(apiClient);
});

class NotificationsRepository {
  NotificationsRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<NotificationItemModel>> getNotifications({
    bool onlyUnread = false,
    int limit = 50,
  }) async {
    final response = await _apiClient.get(
      '/notifications/me',
      queryParameters: {
        'only_unread': onlyUnread,
        'limit': limit,
      },
    );
    return (response as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(NotificationItemModel.fromJson)
        .toList();
  }

  Future<int> getUnreadCount() async {
    final response = await _apiClient.get('/notifications/me/unread-count');
    return UnreadCountModel.fromJson(response as Map<String, dynamic>)
        .unreadCount;
  }

  Future<void> markAsRead(int notificationId) async {
    await _apiClient.post('/notifications/$notificationId/read');
  }

  Future<void> dispatchPending() async {
    await _apiClient.post('/notifications/me/dispatch-pending');
  }

  Future<void> markAllAsRead() async {
    await _apiClient.patch('/notifications/mark-all-read');
  }
}
