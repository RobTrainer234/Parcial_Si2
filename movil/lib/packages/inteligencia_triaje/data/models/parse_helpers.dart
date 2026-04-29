double parseDoubleOrZero(dynamic value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? 0.0;
  return 0.0;
}

double? parseNullableDouble(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

int parseIntOrZero(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? 0;
  return 0;
}

int parseRequiredInt(dynamic value, {required String field}) {
  final parsed = parseNullableInt(value);
  if (parsed == null) {
    throw FormatException('Invalid required integer for $field');
  }
  return parsed;
}

int? parseNullableInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}

DateTime? parseDate(dynamic value) {
  if (value == null) return null;
  return DateTime.tryParse(value.toString());
}
