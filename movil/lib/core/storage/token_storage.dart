abstract class TokenStorage {
  Future<String?> readAccessToken();
  Future<void> saveAccessToken(String token);
  Future<void> clearAccessToken();
}
