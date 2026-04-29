import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class RatingTargetModel {
  final String targetType;
  final int? targetId;
  final String label;

  const RatingTargetModel({
    required this.targetType,
    this.targetId,
    required this.label,
  });

  factory RatingTargetModel.fromJson(Map<String, dynamic> json) {
    return RatingTargetModel(
      targetType: json['target_type'] as String? ?? '',
      targetId: parseNullableInt(json['target_id']),
      label: json['label'] as String? ?? '',
    );
  }
}
