import 'package:dio/dio.dart';

class LocationUtils {
  LocationUtils._();

  static final _cache = <String, String>{};

  static Future<String> getLocationLabel(double lat, double lng) async {
    final key = '${lat.toStringAsFixed(4)},${lng.toStringAsFixed(4)}';

    if (_cache.containsKey(key)) {
      return _cache[key]!;
    }

    try {
      final dio = Dio();
      final response = await dio.get(
        'https://nominatim.openstreetmap.org/reverse',
        queryParameters: {
          'format': 'json',
          'accept-language': 'es',
          'lat': lat,
          'lon': lng,
        },
        options: Options(
          headers: {
            'User-Agent': 'MovilAuxilioVial/1.0',
          },
        ),
      );

      if (response.statusCode == 200 && response.data is Map) {
        final data = response.data as Map<String, dynamic>;
        final displayName = data['display_name'] as String?;
        if (displayName != null && displayName.isNotEmpty) {
          final parts = displayName.split(',').map((p) => p.trim()).toList();
          final short = parts.take(3).join(', ');
          _cache[key] = short;
          return short;
        }
      }
    } catch (_) {}

    _cache[key] = 'Ubicación aproximada';
    return 'Ubicación aproximada';
  }

  static String coordsText(double lat, double lng) {
    return '${lat.toStringAsFixed(4)}, ${lng.toStringAsFixed(4)}';
  }
}
