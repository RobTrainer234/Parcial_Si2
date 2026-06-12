import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class OperatorNavigationMap extends StatefulWidget {
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
    this.hasArrived = false,
  });

  final double? incidentLatitud;
  final double? incidentLongitud;
  final double? operarioLatitud;
  final double? operarioLongitud;
  final DateTime? lastLocationAt;
  final List<LatLng>? routePoints;
  final double? routeDistanceMeters;
  final double? routeDurationSeconds;
  final bool hasArrived;

  @override
  State<OperatorNavigationMap> createState() => _OperatorNavigationMapState();
}

class _OperatorNavigationMapState extends State<OperatorNavigationMap> {
  final MapController _mapController = MapController();
  bool _autoFollow = true;

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(OperatorNavigationMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    final op = _toLatLng(widget.operarioLatitud, widget.operarioLongitud);
    if (op != null && _autoFollow) {
      _mapController.move(op, _mapController.camera.zoom);
    }
  }

  void _recenter() {
    final op = _toLatLng(widget.operarioLatitud, widget.operarioLongitud);
    final inc = _toLatLng(widget.incidentLatitud, widget.incidentLongitud);
    final target = op ?? inc;
    if (target != null) {
      _mapController.move(target, 14.0);
      setState(() => _autoFollow = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final incidentPoint = _toLatLng(widget.incidentLatitud, widget.incidentLongitud);
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
                style: theme.textTheme.bodyMedium,
              ),
            ),
          ),
        ),
      );
    }

    final operarioPoint = _toLatLng(widget.operarioLatitud, widget.operarioLongitud);
    final hasOsrmRoute = widget.routePoints != null && widget.routePoints!.length >= 2;
    final center = operarioPoint ?? incidentPoint;
    final zoom = operarioPoint != null ? 14.5 : 15.0;

    final polylines = <Polyline>[
      if (hasOsrmRoute)
        Polyline(
          points: widget.routePoints!,
          strokeWidth: 5,
          color: Colors.blue.shade600,
        )
      else if (operarioPoint != null)
        Polyline(
          points: [operarioPoint, incidentPoint],
          strokeWidth: 3,
          color: Colors.blue.shade400,
          pattern: StrokePattern.dashed(segments: [10, 6]),
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
          width: 72,
          height: 72,
          child: widget.hasArrived
              ? _OperatorArrivedMarker()
              : _OperatorPositionMarker(),
        ),
    ];

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: SizedBox(
        height: 380,
        child: Stack(
          children: [
            FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: center,
                initialZoom: zoom,
                onMapEvent: (event) {
                  if (event is MapEventMoveEnd && _autoFollow) {
                    final op = _toLatLng(
                      widget.operarioLatitud,
                      widget.operarioLongitud,
                    );
                    if (op != null) {
                      final dist = _distance(event.camera.center, op);
                      if (dist > 0.01) {
                        setState(() => _autoFollow = false);
                      }
                    }
                  }
                },
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
            if (hasOsrmRoute && widget.routeDistanceMeters != null)
              Positioned(
                top: 12,
                left: 12,
                right: 12,
                child: Material(
                  elevation: 3,
                  borderRadius: BorderRadius.circular(12),
                  color: Colors.white,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.route, color: Colors.blue.shade600, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          '${(widget.routeDistanceMeters! / 1000).toStringAsFixed(1)} km',
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 15,
                            color: theme.colorScheme.onSurface,
                          ),
                        ),
                        if (widget.routeDurationSeconds != null) ...[
                          const SizedBox(width: 4),
                          Text(
                            '· ${_formatDuration(widget.routeDurationSeconds!)}',
                            style: TextStyle(
                              color: theme.colorScheme.onSurfaceVariant,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            if (widget.hasArrived)
              Positioned(
                top: 60,
                left: 12,
                right: 12,
                child: Material(
                  elevation: 4,
                  borderRadius: BorderRadius.circular(12),
                  color: Colors.green.shade600,
                  child: const Padding(
                    padding: EdgeInsets.all(14),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle, color: Colors.white, size: 22),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Has llegado al lugar del incidente',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            Positioned(
              right: 12,
              bottom: 48,
              child: FloatingActionButton.small(
                heroTag: 'op_recenter',
                onPressed: _recenter,
                backgroundColor: Colors.white,
                child: Icon(
                  _autoFollow ? Icons.my_location : Icons.location_searching,
                  color: _autoFollow
                      ? Colors.blue.shade600
                      : Colors.grey.shade600,
                  size: 20,
                ),
              ),
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
    );
  }
}

double _distance(LatLng a, LatLng b) {
  return math.sqrt(
    math.pow(a.latitude - b.latitude, 2) +
        math.pow(a.longitude - b.longitude, 2),
  );
}

LatLng? _toLatLng(double? latitud, double? longitud) {
  if (latitud == null || longitud == null) return null;
  return LatLng(latitud, longitud);
}

String _formatDuration(double seconds) {
  final totalMinutes = (seconds / 60).round();
  if (totalMinutes < 60) return '$totalMinutes min';
  final hours = totalMinutes ~/ 60;
  final minutes = totalMinutes % 60;
  if (minutes == 0) return '${hours}h';
  return '${hours}h ${minutes}min';
}

class _OperatorPositionMarker extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          decoration: BoxDecoration(
            color: Colors.green.shade700,
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white, width: 2),
            boxShadow: [
              BoxShadow(
                color: Colors.green.shade700.withValues(alpha: 0.3),
                blurRadius: 10,
                spreadRadius: 2,
              ),
            ],
          ),
          padding: const EdgeInsets.all(10),
          child: const Icon(
            Icons.navigation,
            color: Colors.white,
            size: 22,
          ),
        ),
      ],
    );
  }
}

class _OperatorArrivedMarker extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          decoration: BoxDecoration(
            color: Colors.green.shade600,
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white, width: 3),
            boxShadow: [
              BoxShadow(
                color: Colors.green.shade600.withValues(alpha: 0.4),
                blurRadius: 16,
                spreadRadius: 6,
              ),
            ],
          ),
          padding: const EdgeInsets.all(14),
          child: const Icon(Icons.check_circle, color: Colors.white, size: 28),
        ),
      ],
    );
  }
}

class _MarkerBubble extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  const _MarkerBubble({
    required this.icon,
    required this.color,
    required this.label,
  });

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
          child: Icon(icon, color: Colors.white, size: 24),
        ),
      ),
    );
  }
}
