import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class RatingResponseModel {
  final int serviceId;
  final String actorType;
  final String targetType;
  final int? targetId;
  final int stars;
  final String? comment;
  final int ratingId;
  final bool updatedExisting;
  final double? recipientReputation;
  final String message;

  const RatingResponseModel({
    required this.serviceId,
    required this.actorType,
    required this.targetType,
    this.targetId,
    required this.stars,
    this.comment,
    required this.ratingId,
    required this.updatedExisting,
    this.recipientReputation,
    required this.message,
  });

  factory RatingResponseModel.fromJson(Map<String, dynamic> json) {
    return RatingResponseModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      actorType: json['actor_type'] as String? ?? '',
      targetType: json['target_type'] as String? ?? '',
      targetId: parseNullableInt(json['target_id']),
      stars: parseNullableInt(json['estrellas']) ?? 0,
      comment: json['comentario'] as String?,
      ratingId: parseRequiredInt(json['rating_id'], field: 'rating_id'),
      updatedExisting: json['updated_existing'] as bool? ?? false,
      recipientReputation: parseNullableDouble(json['recipient_reputation']),
      message: json['message'] as String? ?? '',
    );
  }
}
