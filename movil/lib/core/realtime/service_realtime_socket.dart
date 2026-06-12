import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../config/app_config.dart';

enum ServiceRealtimeConnectionState {
  connected,
  reconnecting,
  disconnected,
}

class ServiceRealtimeEvent {
  final String type;
  final int serviceId;
  final int? incidentId;
  final int? workshopId;
  final String? serviceState;
  final DateTime? timestamp;
  final Map<String, dynamic> data;

  const ServiceRealtimeEvent({
    required this.type,
    required this.serviceId,
    required this.incidentId,
    required this.workshopId,
    required this.serviceState,
    required this.timestamp,
    required this.data,
  });

  factory ServiceRealtimeEvent.fromJson(Map<String, dynamic> json) {
    final rawData = json['data'];
    return ServiceRealtimeEvent(
      type: json['type'] as String? ?? '',
      serviceId: (json['service_id'] as num?)?.toInt() ?? 0,
      incidentId: (json['incident_id'] as num?)?.toInt(),
      workshopId: (json['workshop_id'] as num?)?.toInt(),
      serviceState: json['service_state'] as String?,
      timestamp: _parseDate(json['timestamp']),
      data: rawData is Map<String, dynamic>
          ? rawData
          : rawData is Map
              ? rawData.map(
                  (key, value) => MapEntry(key.toString(), value),
                )
              : const <String, dynamic>{},
    );
  }
}

DateTime? _parseDate(dynamic value) {
  if (value is String && value.trim().isNotEmpty) {
    return DateTime.tryParse(value)?.toUtc();
  }
  return null;
}

class ServiceRealtimeSocketSession {
  ServiceRealtimeSocketSession({
    required this.serviceId,
    required this.token,
  }) {
    _emitState(ServiceRealtimeConnectionState.disconnected);
    _connect(isReconnect: false);
  }

  final int serviceId;
  final String token;
  final StreamController<ServiceRealtimeEvent> _eventsController =
      StreamController<ServiceRealtimeEvent>.broadcast();
  final StreamController<ServiceRealtimeConnectionState> _stateController =
      StreamController<ServiceRealtimeConnectionState>.broadcast();

  WebSocketChannel? _socket;
  StreamSubscription<dynamic>? _socketSubscription;
  Timer? _reconnectTimer;
  bool _disposed = false;

  Stream<ServiceRealtimeEvent> get events => _eventsController.stream;
  Stream<ServiceRealtimeConnectionState> get states => _stateController.stream;

  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _socketSubscription?.cancel();
    _socketSubscription = null;
    _socket?.sink.close();
    _socket = null;
    _emitState(ServiceRealtimeConnectionState.disconnected);
    _eventsController.close();
    _stateController.close();
  }

  Future<void> _connect({required bool isReconnect}) async {
    if (_disposed) {
      return;
    }
    if (isReconnect) {
      _emitState(ServiceRealtimeConnectionState.reconnecting);
    }

    try {
      final socket = WebSocketChannel.connect(
        AppConfig.buildWebSocketUri(
          '/ws/services/$serviceId',
          queryParameters: {'token': token},
        ),
      );
      if (_disposed) {
        socket.sink.close();
        return;
      }
      _socket = socket;
      _emitState(ServiceRealtimeConnectionState.connected);
      _socketSubscription = socket.stream.listen(
        _handleMessage,
        onError: (_) => _handleDisconnect(),
        onDone: _handleDisconnect,
        cancelOnError: true,
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _handleMessage(dynamic message) {
    if (_disposed) {
      return;
    }
    try {
      final raw = message is String ? message : utf8.decode(message as List<int>);
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        _eventsController.add(ServiceRealtimeEvent.fromJson(decoded));
      } else if (decoded is Map) {
        _eventsController.add(
          ServiceRealtimeEvent.fromJson(
            decoded.map((key, value) => MapEntry(key.toString(), value)),
          ),
        );
      }
    } catch (_) {}
  }

  void _handleDisconnect() {
    if (_disposed) {
      return;
    }
    _socket?.sink.close();
    _socket = null;
    _socketSubscription?.cancel();
    _socketSubscription = null;
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_disposed || _reconnectTimer != null) {
      return;
    }
    _emitState(ServiceRealtimeConnectionState.reconnecting);
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      _reconnectTimer = null;
      _connect(isReconnect: true);
    });
  }

  void _emitState(ServiceRealtimeConnectionState state) {
    if (!_stateController.isClosed) {
      _stateController.add(state);
    }
  }
}

class ServiceRealtimeSocketService {
  ServiceRealtimeSocketSession connectToService({
    required int serviceId,
    required String token,
  }) {
    return ServiceRealtimeSocketSession(
      serviceId: serviceId,
      token: token,
    );
  }
}

final serviceRealtimeSocketServiceProvider =
    Provider<ServiceRealtimeSocketService>((ref) {
  return ServiceRealtimeSocketService();
});
