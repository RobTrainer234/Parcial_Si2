import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class OperatorNavigationMap extends StatelessWidget {
  const OperatorNavigationMap({
    super.key,
    required this.incidentLatitud,
    required this.incidentLongitud,
    this.operarioLatitud,
    this.operarioLongitud,
    this.lastLocationAt,
    this.routePoints,
    this.routeDistanceMeters,
    this.routeDurationSeconds,
  });

  final double? incidentLatitud;
  final double? incidentLongitud;
  final double? operarioLatitud;
  final double? operarioLongitud;
  final DateTime? lastLocationAt;
  final List<LatLng>? routePoints;
  final double? routeDistanceMeters;
  final double? routeDurationSeconds;

  @override
  Widget build(BuildContext context) {
    final incidentPoint = _toLatLng(incidentLatitud, incidentLongitud);
    if (incidentPoint == null) {
      return Card(
        margin: EdgeInsets.zero,
        child: SizedBox(
          height: 220,
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                'No se puede mostrar el mapa porque la ubicacion del incidente no esta disponible.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ),
        ),
      );
    }

    final operarioPoint = _toLatLng(operarioLatitud, operarioLongitud);
    final hasRoute = routePoints != null && routePoints!.length >= 2;
    final allPoints = <LatLng>[
      ...?routePoints,
      incidentPoint,
      if (operarioPoint != null) operarioPoint,
    ];
    final center = _computeCenter(allPoints);
    final zoom = operarioPoint != null ? 13.5 : 14.5;

    final polylines = <Polyline>[
      if (hasRoute)
        Polyline(
          points: routePoints!,
          strokeWidth: 4,
          color: Colors.blue.shade600,
        )
      else if (operarioPoint != null)
        Polyline(
          points: [operarioPoint, incidentPoint],
          strokeWidth: 4,
          color: Colors.blue.shade600,
        ),
    ];

    final markers = <Marker>[
      Marker(
        point: incidentPoint,
        width: 56,
        height: 56,
        child: _MarkerBubble(
          icon: Icons.location_on,
          color: Colors.red.shade600,
          label: 'Ubicacion del incidente',
        ),
      ),
      if (operarioPoint != null)
        Marker(
          point: operarioPoint,
          width: 56,
          height: 56,
          child: _MarkerBubble(
            icon: Icons.local_shipping,
            color: Colors.green.shade700,
            label: 'Tu ubicacion actual',
          ),
        ),
    ];

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Mapa de asistencia',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              'Usa esta vista para ubicar el incidente y enviar tu posicion al cliente.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            if (hasRoute && routeDistanceMeters != null) ...[
              const SizedBox(height: 4),
              Text(
                'Ruta: ${(routeDistanceMeters! / 1000).toStringAsFixed(1)} km'
                '${routeDurationSeconds != null ? " · ${_formatDuration(routeDurationSeconds!)}" : ""}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                      fontWeight: FontWeight.w600,
                    ),
              ),
            ],
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: SizedBox(
                height: 320,
                child: Stack(
                  children: [
                    FlutterMap(
                      options: MapOptions(
                        initialCenter: center,
                        initialZoom: zoom,
                      ),
                      children: [
                        TileLayer(
                          urlTemplate:
                              'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                          userAgentPackageName: 'si2.auxilio_vial',
                        ),
                        PolylineLayer(polylines: polylines),
                        MarkerLayer(markers: markers),
                      ],
                    ),
                    Positioned(
                      right: 8,
                      bottom: 8,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.92),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          '© OpenStreetMap contributors',
                          style: TextStyle(fontSize: 11),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (lastLocationAt != null) ...[
              const SizedBox(height: 8),
              Text(
                'Ultima actualizacion: ${_formatDate(lastLocationAt)}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

LatLng? _toLatLng(double? latitud, double? longitud) {
  if (latitud == null || longitud == null) {
    return null;
  }
  return LatLng(latitud, longitud);
}

LatLng _computeCenter(List<LatLng> points) {
  if (points.length == 1) {
    return points.first;
  }

  final totalLat = points.fold<double>(0, (sum, point) => sum + point.latitude);
  final totalLng =
      points.fold<double>(0, (sum, point) => sum + point.longitude);
  return LatLng(totalLat / points.length, totalLng / points.length);
}

String _formatDuration(double seconds) {
  final totalMinutes = (seconds / 60).round();
  if (totalMinutes < 60) {
    return '$totalMinutes min';
  }
  final hours = totalMinutes ~/ 60;
  final minutes = totalMinutes % 60;
  if (minutes == 0) return '${hours}h';
  return '${hours}h ${minutes}min';
}

String _formatDate(DateTime? value) {
  if (value == null) {
    return 'Fecha no disponible';
  }
  final localValue = value.toLocal();
  return '${localValue.day.toString().padLeft(2, '0')}/'
      '${localValue.month.toString().padLeft(2, '0')}/'
      '${localValue.year} '
      '${localValue.hour.toString().padLeft(2, '0')}:'
      '${localValue.minute.toString().padLeft(2, '0')}';
}

class _MarkerBubble extends StatelessWidget {
  const _MarkerBubble({
    required this.icon,
    required this.color,
    required this.label,
  });

  final IconData icon;
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: label,
      child: Align(
        alignment: Alignment.topCenter,
        child: Container(
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.18),
                blurRadius: 6,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          padding: const EdgeInsets.all(10),
          child: Icon(
            icon,
            color: Colors.white,
            size: 24,
          ),
        ),
      ),
    );
  }
}
