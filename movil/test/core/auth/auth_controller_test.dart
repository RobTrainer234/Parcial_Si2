import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:movil/core/auth/auth_controller.dart';
import 'package:movil/core/network/api_client.dart';
import 'package:movil/core/storage/secure_storage_service.dart';
import 'package:movil/core/storage/token_storage.dart';
import 'package:movil/packages/seguridad_usuarios/data/models/actor_context_model.dart';
import 'package:movil/packages/seguridad_usuarios/data/models/login_response_model.dart';
import 'package:movil/packages/seguridad_usuarios/data/models/user_profile_model.dart';
import 'package:movil/packages/seguridad_usuarios/data/repositories/auth_repository.dart';

class _FakeTokenStorage implements TokenStorage {
  _FakeTokenStorage({this.readDelay = Duration.zero});

  String? initialToken;
  final Duration readDelay;

  @override
  Future<void> clearAccessToken() async {
    initialToken = null;
  }

  @override
  Future<String?> readAccessToken() async {
    if (readDelay > Duration.zero) {
      await Future<void>.delayed(readDelay);
    }
    return initialToken;
  }

  @override
  Future<void> saveAccessToken(String token) async {
    initialToken = token;
  }
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository({
    required this.loginResponse,
    this.loginDelay = Duration.zero,
  }) : super(ApiClient(Dio()));

  final LoginResponseModel loginResponse;
  final Duration loginDelay;
  UserProfileModel? meResponse;

  @override
  Future<LoginResponseModel> login({
    required String email,
    required String password,
  }) async {
    if (loginDelay > Duration.zero) {
      await Future<void>.delayed(loginDelay);
    }
    return loginResponse;
  }

  @override
  Future<UserProfileModel> me() async {
    return meResponse ?? loginResponse.user;
  }

  @override
  Future<void> logout() async {}
}

void main() {
  test(
    'login keeps authenticated session when startup loadSession finishes later',
    () async {
      const user = UserProfileModel(
        userId: 7,
        personaId: 9,
        role: 'CLIENTE',
        email: 'cliente@test.com',
        phone: '70000000',
        actorContext: ActorContextModel(clientePersonaId: 9),
        homeHint: 'mobile_client_dashboard',
      );
      const loginResponse = LoginResponseModel(
        accessToken: 'token-123',
        tokenType: 'bearer',
        role: 'CLIENTE',
        user: user,
        actorContext: ActorContextModel(clientePersonaId: 9),
        homeHint: 'mobile_client_dashboard',
      );

      final storage = _FakeTokenStorage(
        readDelay: const Duration(milliseconds: 150),
      );
      final repository = _FakeAuthRepository(
        loginResponse: loginResponse,
        loginDelay: const Duration(milliseconds: 10),
      );

      final container = ProviderContainer(
        overrides: [
          tokenStorageProvider.overrideWithValue(storage),
          authRepositoryProvider.overrideWithValue(repository),
          deviceTokenRegistrationProvider.overrideWithValue(() async {}),
        ],
      );
      addTearDown(container.dispose);

      final notifier = container.read(authControllerProvider.notifier);

      await notifier.login('cliente@test.com', 'password123');
      await Future<void>.delayed(const Duration(milliseconds: 220));

      final session = container.read(authControllerProvider).valueOrNull;
      expect(session?.isAuthenticated, isTrue);
      expect(session?.accessToken, 'token-123');
      expect(session?.role, 'CLIENTE');
      expect(session?.user?.userId, 7);
    },
  );
}
