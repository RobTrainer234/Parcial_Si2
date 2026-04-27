import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'token_storage.dart';

final tokenStorageProvider = Provider<TokenStorage>((ref) {
  return SecureStorageService();
});

class SecureStorageService implements TokenStorage {
  static const _accessTokenKey = 'access_token';
  
  final FlutterSecureStorage _storage;

  SecureStorageService() : _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  @override
  Future<String?> readAccessToken() async {
    return await _storage.read(key: _accessTokenKey);
  }

  @override
  Future<void> saveAccessToken(String token) async {
    await _storage.write(key: _accessTokenKey, value: token);
  }

  @override
  Future<void> clearAccessToken() async {
    await _storage.delete(key: _accessTokenKey);
  }
}
