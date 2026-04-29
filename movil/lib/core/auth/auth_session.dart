import '../../packages/seguridad_usuarios/data/models/user_profile_model.dart';

class AuthSession {
  final bool isAuthenticated;
  final String? accessToken;
  final String? role;
  final String? homeHint;
  final UserProfileModel? user;

  const AuthSession({
    this.isAuthenticated = false,
    this.accessToken,
    this.role,
    this.homeHint,
    this.user,
  });

  AuthSession copyWith({
    bool? isAuthenticated,
    String? accessToken,
    String? role,
    String? homeHint,
    UserProfileModel? user,
  }) {
    return AuthSession(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      accessToken: accessToken ?? this.accessToken,
      role: role ?? this.role,
      homeHint: homeHint ?? this.homeHint,
      user: user ?? this.user,
    );
  }
}
