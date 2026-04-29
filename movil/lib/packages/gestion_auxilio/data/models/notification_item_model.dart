import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class NotificationItemModel {
  final int notificationId;
  final int? serviceId;
  final int? requestId;
  final String channel;
  final String title;
  final String message;
  final dynamic payload;
  final String status;
  final String? provider;
  final DateTime? createdAt;
  final DateTime? sentAt;
  final DateTime? readAt;

  const NotificationItemModel({
    required this.notificationId,
    this.serviceId,
    this.requestId,
    required this.channel,
    required this.title,
    required this.message,
    this.payload,
    required this.status,
    this.provider,
    this.createdAt,
    this.sentAt,
    this.readAt,
  });

  bool get isUnread => readAt == null;

  int? get resolvedServiceId {
    if (serviceId != null) return serviceId;
    if (payload is Map) {
      final map = payload as Map;
      return parseNullableInt(map['service_id']);
    }
    return null;
  }

  String? get resolvedServiceState {
    if (payload is Map) {
      final map = payload as Map;
      final state = map['service_state'];
      if (state is String && state.trim().isNotEmpty) {
        return state;
      }
    }
    return null;
  }

  factory NotificationItemModel.fromJson(Map<String, dynamic> json) {
    return NotificationItemModel(
      notificationId:
          parseRequiredInt(json['notification_id'], field: 'notification_id'),
      serviceId: parseNullableInt(json['service_id']),
      requestId: parseNullableInt(json['request_id']),
      channel: json['channel'] as String? ?? '',
      title: json['title'] as String? ?? '',
      message: json['message'] as String? ?? '',
      payload: json['payload'],
      status: json['status'] as String? ?? '',
      provider: json['provider'] as String?,
      createdAt: parseDate(json['created_at']),
      sentAt: parseDate(json['sent_at']),
      readAt: parseDate(json['read_at']),
    );
  }
}
