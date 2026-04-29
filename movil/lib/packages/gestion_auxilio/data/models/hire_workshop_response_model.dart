import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class HireWorkshopResponseModel {
  final int incidentId;
  final int requestId;
  final int workshopId;
  final String workshopName;
  final String requestState;
  final String message;

  const HireWorkshopResponseModel({
    required this.incidentId,
    required this.requestId,
    required this.workshopId,
    required this.workshopName,
    required this.requestState,
    required this.message,
  });

  factory HireWorkshopResponseModel.fromJson(Map<String, dynamic> json) {
    return HireWorkshopResponseModel(
      incidentId: parseIntOrZero(json['incident_id']),
      requestId: parseIntOrZero(json['request_id']),
      workshopId: parseIntOrZero(json['workshop_id']),
      workshopName: json['workshop_name'] as String? ?? '',
      requestState: json['request_state'] as String? ?? '',
      message: json['message'] as String? ?? '',
    );
  }
}
