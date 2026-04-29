import 'actor_context_model.dart';

class UserProfileModel {
  final int userId;
  final int personaId;
  final String role;
  final String email;
  final String? phone;
  final ActorContextModel actorContext;
  final String homeHint;

  const UserProfileModel({
    required this.userId,
    required this.personaId,
    required this.role,
    required this.email,
    this.phone,
    required this.actorContext,
    required this.homeHint,
  });

  factory UserProfileModel.fromJson(Map<String, dynamic> json) {
    return UserProfileModel(
      userId: json['user_id'] as int,
      personaId: json['persona_id'] as int,
      role: json['role'] as String,
      email: json['email'] as String,
      phone: json['phone'] as String?,
      actorContext: ActorContextModel.fromJson(json['actor_context'] as Map<String, dynamic>),
      homeHint: json['home_hint'] as String,
    );
  }
}
