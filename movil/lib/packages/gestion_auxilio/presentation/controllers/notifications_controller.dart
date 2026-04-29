import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../data/models/notification_item_model.dart';
import '../../data/repositories/notifications_repository.dart';

class NotificationsState {
  final List<NotificationItemModel> items;
  final int unreadCount;
  final bool onlyUnread;

  const NotificationsState({
    required this.items,
    required this.unreadCount,
    required this.onlyUnread,
  });
}

final notificationsControllerProvider =
    StateNotifierProvider<
      NotificationsController,
      AsyncValue<NotificationsState>
    >((ref) {
      final repository = ref.watch(notificationsRepositoryProvider);
      final authenticatedUserId = ref.watch(
        authControllerProvider.select(
          (state) => state.valueOrNull?.user?.userId,
        ),
      );
      return NotificationsController(
        ref,
        repository,
        shouldLoad: authenticatedUserId != null,
      );
    });

final unreadNotificationsCountProvider = FutureProvider<int>((ref) async {
  final authenticatedUserId = ref.watch(
    authControllerProvider.select((state) => state.valueOrNull?.user?.userId),
  );
  if (authenticatedUserId == null) {
    return 0;
  }
  final repository = ref.watch(notificationsRepositoryProvider);
  return repository.getUnreadCount();
});

class NotificationsController
    extends StateNotifier<AsyncValue<NotificationsState>> {
  NotificationsController(
    this._ref,
    this._repository, {
    required bool shouldLoad,
  }) : _shouldLoad = shouldLoad,
       super(const AsyncValue.loading()) {
    if (_shouldLoad) {
      load();
    }
  }

  final Ref _ref;
  final NotificationsRepository _repository;
  final bool _shouldLoad;

  Future<void> load({bool onlyUnread = false}) async {
    if (!_shouldLoad) {
      return;
    }
    state = const AsyncValue.loading();
    try {
      final items = await _repository.getNotifications(onlyUnread: onlyUnread);
      final unreadCount = await _repository.getUnreadCount();
      state = AsyncValue.data(
        NotificationsState(
          items: items,
          unreadCount: unreadCount,
          onlyUnread: onlyUnread,
        ),
      );
      _ref.invalidate(unreadNotificationsCountProvider);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refresh() async {
    final onlyUnread = state.valueOrNull?.onlyUnread ?? false;
    try {
      await _repository.dispatchPending();
    } catch (_) {
      // best-effort in dev/sandbox
    }
    await load(onlyUnread: onlyUnread);
  }

  Future<void> setOnlyUnread(bool value) async {
    await load(onlyUnread: value);
  }

  Future<void> markAsRead(int notificationId) async {
    final current = state.valueOrNull;
    if (current == null) return;

    try {
      await _repository.markAsRead(notificationId);
      final updatedItems = [
        for (final item in current.items)
          if (item.notificationId == notificationId)
            NotificationItemModel(
              notificationId: item.notificationId,
              serviceId: item.serviceId,
              requestId: item.requestId,
              channel: item.channel,
              title: item.title,
              message: item.message,
              payload: item.payload,
              status: item.status,
              provider: item.provider,
              createdAt: item.createdAt,
              sentAt: item.sentAt,
              readAt: DateTime.now(),
            )
          else
            item,
      ];
      final unreadCount = await _repository.getUnreadCount();
      state = AsyncValue.data(
        NotificationsState(
          items: current.onlyUnread
              ? updatedItems.where((item) => item.isUnread).toList()
              : updatedItems,
          unreadCount: unreadCount,
          onlyUnread: current.onlyUnread,
        ),
      );
      _ref.invalidate(unreadNotificationsCountProvider);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }
}
