import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../storage/secure_storage_service.dart';
import '../storage/token_storage.dart';
import 'auth_session.dart';

final authControllerProvider = StateNotifierProvider<AuthController, AsyncValue<AuthSession>>((ref) {
  final storage = ref.watch(tokenStorageProvider);
  return AuthController(storage);
});

class AuthController extends StateNotifier<AsyncValue<AuthSession>> {
  final TokenStorage _storage;

  AuthController(this._storage) : super(const AsyncValue.loading()) {
    loadSession();
  }

  Future<void> loadSession() async {
    state = const AsyncValue.loading();
    try {
      final token = await _storage.readAccessToken();
      if (token != null && token.isNotEmpty) {
        state = AsyncValue.data(AuthSession(
          isAuthenticated: true,
          accessToken: token,
        ));
      } else {
        state = const AsyncValue.data(AuthSession());
      }
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> saveSession({
    required String accessToken,
    String? role,
    String? homeHint,
  }) async {
    try {
      await _storage.saveAccessToken(accessToken);
      state = AsyncValue.data(AuthSession(
        isAuthenticated: true,
        accessToken: accessToken,
        role: role,
        homeHint: homeHint,
      ));
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> logout() async {
    try {
      await _storage.clearAccessToken();
      state = const AsyncValue.data(AuthSession());
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}
