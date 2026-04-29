import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class RecommendedWorkshopModel {
  final int workshopId;
  final String workshopName;
  final double latitud;
  final double longitud;
  final double distanceKm;
  final double distanceMeters;
  final double? reputation;
  final bool specialtyMatch;
  final bool insuranceExistsWithWorkshop;
  final bool insurancePriorityApplied;
  final bool insuranceCoveringThisSpecialty;
  final String? coverageName;
  final double? rankingScore;
  final String? estimatedArrivalText;
  final double? estimatedCost;
  final String? currency;
  final String? currentMatchmakingStatus;
  final bool isTopRecommendation;

  const RecommendedWorkshopModel({
    required this.workshopId,
    required this.workshopName,
    required this.latitud,
    required this.longitud,
    required this.distanceKm,
    required this.distanceMeters,
    this.reputation,
    required this.specialtyMatch,
    required this.insuranceExistsWithWorkshop,
    required this.insurancePriorityApplied,
    required this.insuranceCoveringThisSpecialty,
    this.coverageName,
    this.rankingScore,
    this.estimatedArrivalText,
    this.estimatedCost,
    this.currency,
    this.currentMatchmakingStatus,
    required this.isTopRecommendation,
  });

  factory RecommendedWorkshopModel.fromJson(Map<String, dynamic> json) {
    return RecommendedWorkshopModel(
      workshopId: parseIntOrZero(json['workshop_id']),
      workshopName: json['workshop_name'] as String? ?? '',
      latitud: parseDoubleOrZero(json['latitud']),
      longitud: parseDoubleOrZero(json['longitud']),
      distanceKm: parseDoubleOrZero(json['distance_km']),
      distanceMeters: parseDoubleOrZero(json['distance_meters']),
      reputation: parseNullableDouble(json['reputation']),
      specialtyMatch: json['specialty_match'] as bool? ?? false,
      insuranceExistsWithWorkshop:
          json['insurance_exists_with_workshop'] as bool? ?? false,
      insurancePriorityApplied:
          json['insurance_priority_applied'] as bool? ?? false,
      insuranceCoveringThisSpecialty:
          json['insurance_covering_this_specialty'] as bool? ?? false,
      coverageName: json['coverage_name'] as String?,
      rankingScore: parseNullableDouble(json['ranking_score']),
      estimatedArrivalText: json['estimated_arrival_text'] as String?,
      estimatedCost: parseNullableDouble(json['estimated_cost']),
      currency: json['currency'] as String?,
      currentMatchmakingStatus: json['current_matchmaking_status'] as String?,
      isTopRecommendation: json['is_top_recommendation'] as bool? ?? false,
    );
  }
}
