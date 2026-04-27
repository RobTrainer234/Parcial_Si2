class AuthSession {
  final bool isAuthenticated;
  final String? accessToken;
  final String? role;
  final String? homeHint;

  const AuthSession({
    this.isAuthenticated = false,
    this.accessToken,
    this.role,
    this.homeHint,
  });

  AuthSession copyWith({
    bool? isAuthenticated,
    String? accessToken,
    String? role,
    String? homeHint,
  }) {
    return AuthSession(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      accessToken: accessToken ?? this.accessToken,
      role: role ?? this.role,
      homeHint: homeHint ?? this.homeHint,
    );
  }
}
