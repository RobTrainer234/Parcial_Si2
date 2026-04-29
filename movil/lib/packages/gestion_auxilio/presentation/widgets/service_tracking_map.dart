import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../data/models/tracking_history_point_model.dart';

class ServiceTrackingMap extends StatelessWidget {
  const ServiceTrackingMap({
    super.key,
    required this.incidentLatitud,
    required this.incidentLongitud,
    required this.operarioLatitud,
    required this.operarioLongitud,
    required this.historyPoints,
    required this.lastLocationAt,
  });

  final double? incidentLatitud;
  final double? incidentLongitud;
  final double? operarioLatitud;
  final double? operarioLongitud;
  final List<TrackingHistoryPointModel> historyPoints;
  final DateTime? lastLocationAt;

  @override
  Widget build(BuildContext context) {
    final incidentPoint = _toLatLng(incidentLatitud, incidentLongitud);
    final operarioPoint = _toLatLng(operarioLatitud, operarioLongitud);
    final historyLatLng = historyPoints
        .map((point) => _toLatLng(point.latitud, point.longitud))
        .whereType<LatLng>()
        .toList();

    final allPoints = <LatLng>[
      ...historyLatLng,
      if (incidentPoint != null) incidentPoint,
      if (operarioPoint != null) operarioPoint,
    ];

    if (allPoints.isEmpty) {
      return const _MapEmptyState();
    }

    final center = _computeCenter(allPoints);
    final zoom = allPoints.length > 1 ? 12.0 : 15.0;
    final markers = <Marker>[
      if (incidentPoint != null)
        Marker(
          point: incidentPoint,
          width: 56,
          height: 56,
          child: _MarkerBubble(
            icon: Icons.location_on,
            color: Colors.red.shade600,
            label: 'Ubicación del incidente',
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
            label: 'Última ubicación del operario',
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
              'Mapa de seguimiento',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              'Actualización automática cada 10 segundos',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            if (incidentPoint == null) ...[
              const SizedBox(height: 8),
              Text(
                'Ubicación del incidente no disponible en este seguimiento.',
                style: Theme.of(context).textTheme.bodySmall,
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
                        if (historyLatLng.length >= 2)
                          PolylineLayer(
                            polylines: [
                              Polyline(
                                points: historyLatLng,
                                strokeWidth: 4,
                                color: Colors.blue.shade600,
                              ),
                            ],
                          ),
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
                'Última actualización: ${_formatDate(lastLocationAt)}',
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

class _MapEmptyState extends StatelessWidget {
  const _MapEmptyState();

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: SizedBox(
        height: 220,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Aún no hay ubicación disponible para mostrar en el mapa.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ),
      ),
    );
  }
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
