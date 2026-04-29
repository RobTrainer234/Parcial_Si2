import 'persona_profile_model.dart';
import 'operario_specialty_model.dart';
import 'user_profile_model.dart';
import 'vehicle_model.dart';

class ProfileMeModel {
  final PersonaProfileModel persona;
  final UserProfileModel user;
  final List<VehicleModel> vehicles;
  final List<OperarioSpecialtyModel> specialties;

  const ProfileMeModel({
    required this.persona,
    required this.user,
    required this.vehicles,
    this.specialties = const [],
  });

  factory ProfileMeModel.fromJson(Map<String, dynamic> json) {
    return ProfileMeModel(
      persona: PersonaProfileModel.fromJson(
        json['persona'] as Map<String, dynamic>,
      ),
      user: UserProfileModel.fromJson(json['user'] as Map<String, dynamic>),
      vehicles:
          (json['vehicles'] as List<dynamic>?)
              ?.map((v) => VehicleModel.fromJson(v as Map<String, dynamic>))
              .toList() ??
          [],
      specialties:
          (json['specialties'] as List<dynamic>?)
              ?.map(
                (item) => OperarioSpecialtyModel.fromJson(
                  item as Map<String, dynamic>,
                ),
              )
              .toList() ??
          const [],
    );
  }
}
