import 'actor_context_model.dart';
import 'user_profile_model.dart';

class LoginResponseModel {
  final String accessToken;
  final String tokenType;
  final String role;
  final UserProfileModel user;
  final ActorContextModel actorContext;
  final String homeHint;

  const LoginResponseModel({
    required this.accessToken,
    required this.tokenType,
    required this.role,
    required this.user,
    required this.actorContext,
    required this.homeHint,
  });

  factory LoginResponseModel.fromJson(Map<String, dynamic> json) {
    return LoginResponseModel(
      accessToken: json['access_token'] as String,
      tokenType: json['token_type'] as String,
      role: json['role'] as String,
      user: UserProfileModel.fromJson(json['user'] as Map<String, dynamic>),
      actorContext: ActorContextModel.fromJson(json['actor_context'] as Map<String, dynamic>),
      homeHint: json['home_hint'] as String,
    );
  }
}
