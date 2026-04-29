import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../packages/seguridad_usuarios/data/repositories/auth_repository.dart';
import '../storage/secure_storage_service.dart';
import '../storage/token_storage.dart';
import 'auth_session.dart';

final authControllerProvider =
    StateNotifierProvider<AuthController, AsyncValue<AuthSession>>((ref) {
  final storage = ref.watch(tokenStorageProvider);
  final authRepository = ref.watch(authRepositoryProvider);
  return AuthController(storage, authRepository);
});

class AuthController extends StateNotifier<AsyncValue<AuthSession>> {
  final TokenStorage _storage;
  final AuthRepository _authRepository;

  AuthController(this._storage, this._authRepository)
      : super(const AsyncValue.loading()) {
    loadSession();
  }

  String _normalizeRole(String? role) {
    final normalized = (role ?? '').trim().toUpperCase();
    if (normalized == 'ADMIN') {
      return 'ADMINISTRADOR';
    }
    return normalized;
  }

  Future<void> loadSession() async {
    state = const AsyncValue.loading();
    try {
      final token = await _storage.readAccessToken();
      if (token != null && token.isNotEmpty) {
        final userProfile = await _authRepository.me();
        state = AsyncValue.data(
          AuthSession(
            isAuthenticated: true,
            accessToken: token,
            role: _normalizeRole(userProfile.role),
            homeHint: userProfile.homeHint,
            user: userProfile,
          ),
        );
      } else {
        state = const AsyncValue.data(AuthSession());
      }
    } catch (_) {
      await _storage.clearAccessToken();
      state = const AsyncValue.data(AuthSession());
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final response = await _authRepository.login(
        email: email,
        password: password,
      );

      await _storage.saveAccessToken(response.accessToken);
      state = AsyncValue.data(
        AuthSession(
          isAuthenticated: true,
          accessToken: response.accessToken,
          role: _normalizeRole(response.role),
          homeHint: response.homeHint,
          user: response.user,
        ),
      );
    } catch (e) {
      state = const AsyncValue.data(AuthSession());
      rethrow;
    }
  }

  Future<void> logout() async {
    try {
      if (state.valueOrNull?.isAuthenticated == true) {
        await _authRepository.logout();
      }
    } catch (_) {
      // Ignora errores de logout backend para forzar cierre local.
    } finally {
      await _storage.clearAccessToken();
      state = const AsyncValue.data(AuthSession());
    }
  }
}
