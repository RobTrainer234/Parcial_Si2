import 'package:flutter/material.dart';

import '../utils/location_utils.dart';

class LocationLabel extends StatefulWidget {
  const LocationLabel({
    super.key,
    required this.latitud,
    required this.longitud,
  });

  final double latitud;
  final double longitud;

  @override
  State<LocationLabel> createState() => _LocationLabelState();
}

class _LocationLabelState extends State<LocationLabel> {
  String? _label;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final label = await LocationUtils.getLocationLabel(
      widget.latitud,
      widget.longitud,
    );
    if (mounted) {
      setState(() {
        _label = label;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final coords = LocationUtils.coordsText(widget.latitud, widget.longitud);
    final primary = _loading ? 'Ubicación aproximada' : _label!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(primary, style: theme.textTheme.bodyLarge),
        const SizedBox(height: 2),
        Text(
          coords,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}
