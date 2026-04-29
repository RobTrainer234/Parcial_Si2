import '../../../inteligencia_triaje/data/models/parse_helpers.dart';
import 'incident_diagnosis_summary_model.dart';
import 'recommended_workshop_model.dart';

class IncidentRecommendationsModel {
  final IncidentDiagnosisSummaryModel diagnosis;
  final List<RecommendedWorkshopModel> recommendedWorkshops;
  final bool hasRecommendations;
  final int? topRecommendationWorkshopId;
  final String message;

  const IncidentRecommendationsModel({
    required this.diagnosis,
    required this.recommendedWorkshops,
    required this.hasRecommendations,
    this.topRecommendationWorkshopId,
    required this.message,
  });

  factory IncidentRecommendationsModel.fromJson(Map<String, dynamic> json) {
    return IncidentRecommendationsModel(
      diagnosis: IncidentDiagnosisSummaryModel.fromJson(
        (json['diagnosis'] as Map<String, dynamic>?) ?? <String, dynamic>{},
      ),
      recommendedWorkshops:
          (json['recommended_workshops'] as List<dynamic>? ?? const [])
              .whereType<Map<String, dynamic>>()
              .map(RecommendedWorkshopModel.fromJson)
              .toList(),
      hasRecommendations: json['has_recommendations'] as bool? ?? false,
      topRecommendationWorkshopId:
          parseNullableInt(json['top_recommendation_workshop_id']),
      message: json['message'] as String? ?? '',
    );
  }
}
