class RealtimeEvent {
  const RealtimeEvent({
    required this.event,
    required this.transport,
    required this.data,
  });

  final String event;
  final String transport;
  final Map<String, dynamic> data;

  int? get notificationId => _asInt(data['notification_id']);
  int? get serviceId => _asInt(data['service_id']);
  bool get isNotification => event == 'notification.created';

  static int? _asInt(dynamic value) {
    if (value is int) return value;
    return int.tryParse(value?.toString() ?? '');
  }

  factory RealtimeEvent.fromJson(Map<String, dynamic> json) {
    return RealtimeEvent(
      event: json['event']?.toString() ?? 'unknown',
      transport: json['transport']?.toString() ?? 'websocket',
      data: json,
    );
  }
}
