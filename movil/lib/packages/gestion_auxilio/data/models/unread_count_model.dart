import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class UnreadCountModel {
  final int unreadCount;

  const UnreadCountModel({
    required this.unreadCount,
  });

  factory UnreadCountModel.fromJson(Map<String, dynamic> json) {
    return UnreadCountModel(
      unreadCount:
          parseRequiredInt(json['unread_count'], field: 'unread_count'),
    );
  }
}
