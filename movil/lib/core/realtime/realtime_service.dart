import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../auth/auth_controller.dart';
import '../config/app_config.dart';
import 'realtime_event.dart';

enum RealtimeConnectionStatus { disconnected, connecting, connected }

final realtimeServiceProvider = Provider<RealtimeService>((ref) {
  final token = ref.watch(
    authControllerProvider.select((state) => state.valueOrNull?.accessToken),
  );
  final service = RealtimeService(token: token);
  ref.onDispose(service.dispose);
  return service;
});

final realtimeEventsProvider = StreamProvider<RealtimeEvent>((ref) {
  return ref.watch(realtimeServiceProvider).events;
});

final realtimeConnectionStatusProvider =
    StreamProvider<RealtimeConnectionStatus>((ref) {
  return ref.watch(realtimeServiceProvider).statuses;
});

class RealtimeService {
  RealtimeService({required String? token}) : _token = token {
    if (_token?.isNotEmpty == true) {
      _connect();
    }
  }

  final String? _token;
  final _events = StreamController<RealtimeEvent>.broadcast();
  final _statuses = StreamController<RealtimeConnectionStatus>.broadcast();
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _reconnectTimer;
  int _cursor = 0;
  bool _disposed = false;
  RealtimeConnectionStatus _status = RealtimeConnectionStatus.disconnected;

  Stream<RealtimeEvent> get events => _events.stream;
  Stream<RealtimeConnectionStatus> get statuses async* {
    yield _status;
    yield* _statuses.stream;
  }

  void _setStatus(RealtimeConnectionStatus value) {
    _status = value;
    _statuses.add(value);
  }

  void _connect() {
    final token = _token;
    if (_disposed || token == null || token.isEmpty) return;
    _setStatus(RealtimeConnectionStatus.connecting);
    final uri = Uri.parse(AppConfig.realtimeWebSocketUrl).replace(
      queryParameters: {'token': token, 'cursor': '$_cursor'},
    );
    debugPrint('RealtimeService: connecting to ${uri.replace(queryParameters: const {})}');
    try {
      _channel = WebSocketChannel.connect(uri);
      _subscription = _channel!.stream.listen(
        _handleMessage,
        onError: (_) => _scheduleReconnect(),
        onDone: _scheduleReconnect,
        cancelOnError: true,
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _handleMessage(dynamic raw) {
    try {
      final decoded = jsonDecode(raw.toString());
      if (decoded is! Map<String, dynamic>) return;
      final event = RealtimeEvent.fromJson(decoded);
      if (event.event == 'connection.ready') {
        _setStatus(RealtimeConnectionStatus.connected);
      }
      final notificationId = event.notificationId;
      if (notificationId != null && notificationId > _cursor) {
        _cursor = notificationId;
      }
      _events.add(event);
    } catch (error) {
      debugPrint('RealtimeService: ignored invalid event ($error)');
    }
  }

  void _scheduleReconnect() {
    if (_disposed) return;
    _setStatus(RealtimeConnectionStatus.disconnected);
    _subscription?.cancel();
    _subscription = null;
    _channel = null;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), _connect);
  }

  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _subscription?.cancel();
    _channel?.sink.close();
    _events.close();
    _statuses.close();
  }
}
