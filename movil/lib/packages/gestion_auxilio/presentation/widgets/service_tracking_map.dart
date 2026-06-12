import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../data/models/tracking_history_point_model.dart';

class ServiceTrackingMap extends StatefulWidget {
  const ServiceTrackingMap({
    super.key,
    required this.incidentLatitud,
    required this.incidentLongitud,
    required this.operarioLatitud,
    required this.operarioLongitud,
    required this.historyPoints,
    required this.lastLocationAt,
    this.routePoints,
    this.hasArrived = false,
  });

  final double? incidentLatitud;
  final double? incidentLongitud;
  final double? operarioLatitud;
  final double? operarioLongitud;
  final List<TrackingHistoryPointModel> historyPoints;
  final DateTime? lastLocationAt;
  final List<LatLng>? routePoints;
  final bool hasArrived;

  @override
  State<ServiceTrackingMap> createState() => _ServiceTrackingMapState();
}

class _ServiceTrackingMapState extends State<ServiceTrackingMap>
    with TickerProviderStateMixin {
  final MapController _mapController = MapController();
  bool _autoFollow = true;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.7, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _mapController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(ServiceTrackingMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    final op = _toLatLng(widget.operarioLatitud, widget.operarioLongitud);
    if (op != null && _autoFollow) {
      _mapController.move(op, _mapController.camera.zoom);
    }
    if (widget.hasArrived && !oldWidget.hasArrived) {
      _pulseController.repeat(reverse: true);
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
    final incidentPoint =
        _toLatLng(widget.incidentLatitud, widget.incidentLongitud);
    final operarioPoint =
        _toLatLng(widget.operarioLatitud, widget.operarioLongitud);
    final historyLatLng = widget.historyPoints
        .map((point) => _toLatLng(point.latitud, point.longitud))
        .whereType<LatLng>()
        .toList();
    final routeLatLng = widget.routePoints ?? const <LatLng>[];

    final allPoints = <LatLng>[
      ...routeLatLng,
      ...historyLatLng,
      if (incidentPoint != null) incidentPoint,
      if (operarioPoint != null) operarioPoint,
    ];

    if (allPoints.isEmpty) {
      return const _MapEmptyState();
    }

    final center = operarioPoint ?? incidentPoint ?? allPoints.first;
    final zoom = operarioPoint != null ? 14.0 : 15.0;
    final hasDirectRoute = operarioPoint != null && incidentPoint != null;

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
          width: 80,
          height: 80,
          child: widget.hasArrived
              ? _ArrivedMarker()
              : AnimatedBuilder(
                  animation: _pulseAnimation,
                  builder: (context, child) => _PulsingMarker(
                    scale: _pulseAnimation.value,
                    label: 'Operario',
                  ),
                ),
        ),
    ];

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: SizedBox(
        height: 360,
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
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'si2.auxilio_vial',
                ),
                if (routeLatLng.length >= 2)
                  PolylineLayer(
                    polylines: [
                      Polyline(
                        points: routeLatLng,
                        strokeWidth: 4,
                        color: Colors.indigo.shade500,
                      ),
                    ],
                  )
                else if (historyLatLng.length >= 2)
                  PolylineLayer(
                    polylines: [
                      Polyline(
                        points: historyLatLng,
                        strokeWidth: 4,
                        color: Colors.blue.shade600,
                      ),
                    ],
                  )
                else if (hasDirectRoute)
                  PolylineLayer(
                    polylines: [
                      Polyline(
                        points: [operarioPoint, incidentPoint],
                        strokeWidth: 3,
                        color: Colors.blue.shade400,
                        pattern: StrokePattern.dashed(segments: [10, 6]),
                      ),
                    ],
                  ),
                MarkerLayer(markers: markers),
              ],
            ),
            if (widget.hasArrived)
              Positioned(
                top: 16,
                left: 16,
                right: 16,
                child: Material(
                  elevation: 4,
                  borderRadius: BorderRadius.circular(12),
                  color: Colors.green.shade600,
                  child: const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle, color: Colors.white),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'El operario llegó al lugar',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                              fontSize: 15,
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
              child: Column(
                children: [
                  FloatingActionButton.small(
                    heroTag: 'recenter',
                    onPressed: _recenter,
                    backgroundColor: Colors.white,
                    child: Icon(
                      _autoFollow
                          ? Icons.my_location
                          : Icons.location_searching,
                      color: _autoFollow
                          ? Colors.blue.shade600
                          : Colors.grey.shade600,
                      size: 20,
                    ),
                  ),
                ],
              ),
            ),
            Positioned(
              right: 8,
              bottom: 8,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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

class _PulsingMarker extends StatelessWidget {
  final double scale;
  final String label;

  const _PulsingMarker({required this.scale, required this.label});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          decoration: BoxDecoration(
            color: Colors.green.shade700,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Colors.green.shade700.withValues(alpha: 0.3 * scale),
                blurRadius: 12 * scale,
                spreadRadius: 4 * scale,
              ),
            ],
          ),
          padding: EdgeInsets.all(12 * scale),
          child: Icon(
            Icons.local_shipping,
            color: Colors.white,
            size: 24 * scale,
          ),
        ),
      ],
    );
  }
}

class _ArrivedMarker extends StatelessWidget {
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
