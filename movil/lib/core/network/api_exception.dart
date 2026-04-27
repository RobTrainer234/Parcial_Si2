class ApiException implements Exception {
  final int? statusCode;
  final String message;
  final dynamic details;

  ApiException({
    this.statusCode,
    required this.message,
    this.details,
  });

  @override
  String toString() => message;
}
