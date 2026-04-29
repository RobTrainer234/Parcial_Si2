import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/client_register_start_request_model.dart';
import '../models/login_response_model.dart';
import '../models/registration_verify_response_model.dart';
import '../models/user_profile_model.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthRepository(apiClient);
});

class AuthRepository {
  final ApiClient _apiClient;

  AuthRepository(this._apiClient);

  Future<LoginResponseModel> login({
    required String email,
    required String password,
  }) async {
    final response = await _apiClient.post(
      '/auth/login',
      data: {'email': email, 'password': password},
      requiresAuth: false,
    );
    return LoginResponseModel.fromJson(response as Map<String, dynamic>);
  }

  Future<UserProfileModel> me() async {
    final response = await _apiClient.get('/auth/me', requiresAuth: true);
    return UserProfileModel.fromJson(response as Map<String, dynamic>);
  }

  Future<void> logout() async {
    await _apiClient.post('/auth/logout', requiresAuth: true);
  }

  Future<RegistrationVerifyResponseModel> startClientRegistration(
    ClientRegisterStartRequestModel request,
  ) async {
    final response = await _apiClient.post(
      '/auth/register/client/start',
      data: request.toJson(),
      requiresAuth: false,
    );
    return RegistrationVerifyResponseModel.fromJson(
      response as Map<String, dynamic>,
    );
  }

  Future<RegistrationVerifyResponseModel> verifyClientRegistration({
    required String registrationToken,
    required String verificationCode,
  }) async {
    final response = await _apiClient.post(
      '/auth/register/client/verify',
      data: {
        'registration_token': registrationToken,
        'verification_code': verificationCode,
      },
      requiresAuth: false,
    );
    return RegistrationVerifyResponseModel.fromJson(
      response as Map<String, dynamic>,
    );
  }
}
