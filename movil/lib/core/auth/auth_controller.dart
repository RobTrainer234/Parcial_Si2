import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../packages/seguridad_usuarios/data/repositories/auth_repository.dart';
import '../network/api_client.dart';
import '../notifications/device_token_service.dart';
import '../notifications/firebase_messaging_service.dart';
import '../storage/secure_storage_service.dart';
import '../storage/token_storage.dart';
import 'auth_session.dart';

final authControllerProvider =
    StateNotifierProvider<AuthController, AsyncValue<AuthSession>>((ref) {
      final storage = ref.watch(tokenStorageProvider);
      final authRepository = ref.watch(authRepositoryProvider);
      final registerDeviceToken = ref.watch(deviceTokenRegistrationProvider);
      return AuthController(storage, authRepository, registerDeviceToken);
    });

typedef DeviceTokenRegistrationCallback = Future<void> Function();

final deviceTokenRegistrationProvider =
    Provider<DeviceTokenRegistrationCallback>((ref) {
      return () async {
        try {
          final apiClient = ref.read(apiClientProvider);
          final messaging = FirebaseMessagingService.instance;
          final tokenService = DeviceTokenService(apiClient);
          await messaging.initialize();
          final token = await messaging.getToken();
          if (token == null) return;
          String platform;
          try {
            platform = defaultTargetPlatform == TargetPlatform.iOS
                ? 'IOS'
                : 'ANDROID';
          } catch (_) {
            platform = 'ANDROID';
          }
          await tokenService.registerToken(
            deviceToken: token,
            platform: platform,
          );
        } catch (_) {
          debugPrint('AuthController: device token registration skipped');
        }
      };
    });

class AuthController extends StateNotifier<AsyncValue<AuthSession>> {
  final TokenStorage _storage;
  final AuthRepository _authRepository;
  final DeviceTokenRegistrationCallback _registerDeviceTokenCallback;
  int _requestVersion = 0;

  AuthController(
    this._storage,
    this._authRepository,
    this._registerDeviceTokenCallback,
  ) : super(const AsyncValue.loading()) {
    loadSession();
  }

  String _normalizeRole(String? role) {
    final normalized = (role ?? '').trim().toUpperCase();
    if (normalized == 'ADMIN') {
      return 'ADMINISTRADOR';
    }
    return normalized;
  }

  int _beginRequest() {
    _requestVersion += 1;
    return _requestVersion;
  }

  bool _isCurrentRequest(int requestVersion) {
    return _requestVersion == requestVersion;
  }

  Future<void> loadSession() async {
    final requestVersion = _beginRequest();
    debugPrint(
      'AuthController.loadSession: start requestVersion=$requestVersion',
    );
    state = const AsyncValue.loading();
    try {
      final token = await _storage.readAccessToken();
      if (!_isCurrentRequest(requestVersion)) {
        debugPrint(
          'AuthController.loadSession: ignored stale token read requestVersion=$requestVersion',
        );
        return;
      }
      if (token != null && token.isNotEmpty) {
        final userProfile = await _authRepository.me();
        if (!_isCurrentRequest(requestVersion)) {
          debugPrint(
            'AuthController.loadSession: ignored stale profile requestVersion=$requestVersion',
          );
          return;
        }
        state = AsyncValue.data(
          AuthSession(
            isAuthenticated: true,
            accessToken: token,
            role: _normalizeRole(userProfile.role),
            homeHint: userProfile.homeHint,
            user: userProfile,
          ),
        );
        debugPrint(
          'AuthController.loadSession: restored session role=${userProfile.role}',
        );
        unawaited(_registerDeviceToken());
      } else {
        debugPrint('AuthController.loadSession: no stored token');
        state = const AsyncValue.data(AuthSession());
      }
    } catch (_) {
      if (!_isCurrentRequest(requestVersion)) {
        debugPrint(
          'AuthController.loadSession: ignored stale error requestVersion=$requestVersion',
        );
        return;
      }
      await _storage.clearAccessToken();
      if (!_isCurrentRequest(requestVersion)) {
        debugPrint(
          'AuthController.loadSession: ignored stale post-clear requestVersion=$requestVersion',
        );
        return;
      }
      debugPrint('AuthController.loadSession: failed, clearing local session');
      state = const AsyncValue.data(AuthSession());
    }
  }

  Future<void> login(String email, String password) async {
    final requestVersion = _beginRequest();
    debugPrint(
      'AuthController.login: start requestVersion=$requestVersion email=$email',
    );
    state = const AsyncValue.loading();
    try {
      final response = await _authRepository.login(
        email: email,
        password: password,
      );

      await _storage.saveAccessToken(response.accessToken);
      if (!_isCurrentRequest(requestVersion)) {
        debugPrint(
          'AuthController.login: ignored stale login success requestVersion=$requestVersion',
        );
        return;
      }
      state = AsyncValue.data(
        AuthSession(
          isAuthenticated: true,
          accessToken: response.accessToken,
          role: _normalizeRole(response.role),
          homeHint: response.homeHint,
          user: response.user,
        ),
      );
      debugPrint(
        'AuthController.login: authenticated role=${response.role} homeHint=${response.homeHint}',
      );
      unawaited(_registerDeviceToken());
    } catch (e) {
      if (_isCurrentRequest(requestVersion)) {
        debugPrint(
          'AuthController.login: failed requestVersion=$requestVersion error=$e',
        );
        state = const AsyncValue.data(AuthSession());
      }
      rethrow;
    }
  }

  Future<void> _registerDeviceToken() async {
    await _registerDeviceTokenCallback();
  }

  Future<void> logout() async {
    _beginRequest();
    debugPrint('AuthController.logout: start');
    try {
      if (state.valueOrNull?.isAuthenticated == true) {
        await _authRepository.logout();
      }
    } catch (_) {
      // Ignora errores de logout backend para forzar cierre local.
    } finally {
      await _storage.clearAccessToken();
      debugPrint('AuthController.logout: local session cleared');
      state = const AsyncValue.data(AuthSession());
    }
  }
}
