import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class ExistingRatingModel {
  final int ratingId;
  final String targetType;
  final int? targetId;
  final int stars;
  final String? comment;
  final DateTime? ratedAt;

  const ExistingRatingModel({
    required this.ratingId,
    required this.targetType,
    this.targetId,
    required this.stars,
    this.comment,
    this.ratedAt,
  });

  factory ExistingRatingModel.fromJson(Map<String, dynamic> json) {
    return ExistingRatingModel(
      ratingId: parseRequiredInt(json['rating_id'], field: 'rating_id'),
      targetType: json['target_type'] as String? ?? '',
      targetId: parseNullableInt(json['target_id']),
      stars: parseNullableInt(json['estrellas']) ?? 0,
      comment: json['comentario'] as String?,
      ratedAt: parseDate(json['fecha']),
    );
  }
}
