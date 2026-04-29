import '../../../inteligencia_triaje/data/models/parse_helpers.dart';
import 'existing_rating_model.dart';
import 'rating_target_model.dart';

class RatingStatusModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final String actorType;
  final List<RatingTargetModel> allowedTargets;
  final List<ExistingRatingModel> existingRatings;

  const RatingStatusModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.actorType,
    required this.allowedTargets,
    required this.existingRatings,
  });

  factory RatingStatusModel.fromJson(Map<String, dynamic> json) {
    final rawTargets = json['allowed_targets'];
    final rawRatings = json['existing_ratings'];
    return RatingStatusModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      actorType: json['actor_type'] as String? ?? '',
      allowedTargets: rawTargets is List
          ? rawTargets
              .whereType<Map<String, dynamic>>()
              .map(RatingTargetModel.fromJson)
              .toList()
          : const [],
      existingRatings: rawRatings is List
          ? rawRatings
              .whereType<Map<String, dynamic>>()
              .map(ExistingRatingModel.fromJson)
              .toList()
          : const [],
    );
  }
}
