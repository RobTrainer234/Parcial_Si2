import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../../seguridad_usuarios/data/models/vehicle_model.dart';
import '../../../seguridad_usuarios/presentation/controllers/profile_controller.dart';
import '../../data/models/specialty_model.dart';
import '../controllers/incident_report_controller.dart';

enum _LocationUiState {
  pending,
  success,
  error,
}

class IncidentReportPage extends ConsumerStatefulWidget {
  const IncidentReportPage({super.key});

  @override
  ConsumerState<IncidentReportPage> createState() => _IncidentReportPageState();
}

class _IncidentReportPageState extends ConsumerState<IncidentReportPage> {
  final _formKey = GlobalKey<FormState>();
  final _latController = TextEditingController();
  final _lonController = TextEditingController();
  final _descController = TextEditingController();
  final _imagePicker = ImagePicker();

  bool _isSubmitting = false;
  bool _isGettingLocation = false;
  bool _isPickingImages = false;
  bool _showManualLocation = false;

  VehicleModel? _selectedVehicle;
  SpecialtyModel? _selectedSpecialty;
  double? _selectedLatitud;
  double? _selectedLongitud;
  _LocationUiState _locationUiState = _LocationUiState.pending;
  String _locationMessage = 'Ubicación pendiente.';
  List<XFile> _selectedImages = const [];

  @override
  void dispose() {
    _latController.dispose();
    _lonController.dispose();
    _descController.dispose();
    super.dispose();
  }

  void _showMessage(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Theme.of(context).colorScheme.error : null,
      ),
    );
  }

  void _setLocation({
    required double latitud,
    required double longitud,
    required String message,
  }) {
    setState(() {
      _selectedLatitud = latitud;
      _selectedLongitud = longitud;
      _latController.text = latitud.toStringAsFixed(6);
      _lonController.text = longitud.toStringAsFixed(6);
      _locationUiState = _LocationUiState.success;
      _locationMessage = message;
    });
  }

  void _setLocationError(String message) {
    setState(() {
      _selectedLatitud = null;
      _selectedLongitud = null;
      _locationUiState = _LocationUiState.error;
      _locationMessage = message;
    });
  }

  Future<void> _useCurrentLocation() async {
    if (_isGettingLocation || _isSubmitting) return;

    setState(() {
      _isGettingLocation = true;
    });

    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        _setLocationError(
          'Activa la ubicación del dispositivo o ingresa la ubicación manualmente.',
        );
        return;
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        _setLocationError(
          'No se pudo obtener tu ubicación. Puedes ingresarla manualmente.',
        );
        return;
      }

      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 15),
        ),
      );

      _setLocation(
        latitud: position.latitude,
        longitud: position.longitude,
        message: 'Ubicación detectada correctamente.',
      );
    } on TimeoutException {
      _setLocationError(
        'No se pudo obtener la ubicación. Intenta nuevamente o ingrésala manualmente.',
      );
    } on LocationServiceDisabledException {
      _setLocationError(
        'Activa la ubicación del dispositivo o ingresa la ubicación manualmente.',
      );
    } catch (_) {
      _setLocationError(
        'No se pudo obtener la ubicación. Intenta nuevamente o ingrésala manualmente.',
      );
    } finally {
      if (mounted) {
        setState(() {
          _isGettingLocation = false;
        });
      }
    }
  }

  Future<void> _pickImages() async {
    if (_isPickingImages || _isSubmitting) return;
    setState(() => _isPickingImages = true);
    try {
      final picked = await _imagePicker.pickMultiImage();
      if (picked.isEmpty) return;

      final merged = [..._selectedImages, ...picked];
      final uniqueByPath = <String, XFile>{};
      for (final file in merged) {
        uniqueByPath[file.path] = file;
      }

      final limited = uniqueByPath.values.take(5).toList(growable: false);
      setState(() {
        _selectedImages = limited;
      });

      if (merged.length > 5) {
        _showMessage('Solo puedes adjuntar hasta 5 fotos.');
      }
    } catch (_) {
      _showMessage(
        'No se pudieron seleccionar las fotos. Intenta nuevamente.',
        isError: true,
      );
    } finally {
      if (mounted) {
        setState(() => _isPickingImages = false);
      }
    }
  }

  void _removeImage(XFile image) {
    setState(() {
      _selectedImages =
          _selectedImages.where((item) => item.path != image.path).toList();
    });
  }

  void _syncManualLocation() {
    final lat = double.tryParse(_latController.text.trim());
    final lon = double.tryParse(_lonController.text.trim());

    if (lat == null || lon == null) return;
    if (lat < -90 || lat > 90) return;
    if (lon < -180 || lon > 180) return;

    setState(() {
      _selectedLatitud = lat;
      _selectedLongitud = lon;
      _locationUiState = _LocationUiState.success;
      _locationMessage = 'Ubicación manual lista para enviar.';
    });
  }

  ({double latitud, double longitud})? _resolveCoordinates() {
    if (_showManualLocation) {
      final lat = double.tryParse(_latController.text.trim());
      final lon = double.tryParse(_lonController.text.trim());
      if (lat == null || lon == null) return null;
      if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
      return (latitud: lat, longitud: lon);
    }

    if (_selectedLatitud != null && _selectedLongitud != null) {
      return (
        latitud: _selectedLatitud!,
        longitud: _selectedLongitud!,
      );
    }

    return null;
  }

  String? _validateManualLatitude(String? value) {
    if (!_showManualLocation) return null;
    if (value == null || value.trim().isEmpty) return 'Ingresa una latitud';
    final lat = double.tryParse(value.trim());
    if (lat == null) return 'Número no válido';
    if (lat < -90 || lat > 90) return 'Debe estar entre -90 y 90';
    return null;
  }

  String? _validateManualLongitude(String? value) {
    if (!_showManualLocation) return null;
    if (value == null || value.trim().isEmpty) return 'Ingresa una longitud';
    final lon = double.tryParse(value.trim());
    if (lon == null) return 'Número no válido';
    if (lon < -180 || lon > 180) return 'Debe estar entre -180 y 180';
    return null;
  }

  List<SpecialtyModel> _sortSpecialties(List<SpecialtyModel> specialties) {
    final sorted = [...specialties];
    sorted.sort((a, b) {
      final aIsGeneral = _isGeneralSpecialty(a);
      final bIsGeneral = _isGeneralSpecialty(b);
      if (aIsGeneral && !bIsGeneral) return -1;
      if (!aIsGeneral && bIsGeneral) return 1;
      return a.nombre.toLowerCase().compareTo(b.nombre.toLowerCase());
    });
    return sorted;
  }

  bool _isGeneralSpecialty(SpecialtyModel specialty) {
    final value = specialty.nombre.toUpperCase();
    return value.contains('DIAGNOSTICO_GENERAL') ||
        value.contains('DIAGNÓSTICO_GENERAL') ||
        value == 'GENERAL' ||
        value.contains('MECANICA_GENERAL') ||
        value.contains('MECÁNICA_GENERAL');
  }

  String _specialtyDisplayName(SpecialtyModel specialty) {
    final normalized = specialty.nombre.toUpperCase();
    if (normalized.contains('DIAGNOSTICO_GENERAL') ||
        normalized.contains('DIAGNÓSTICO_GENERAL') ||
        normalized == 'GENERAL') {
      return 'No estoy seguro / diagnóstico general';
    }
    if (normalized.contains('MECANICA_GENERAL') ||
        normalized.contains('MECÁNICA_GENERAL')) {
      return 'Mecánica general';
    }
    return specialty.nombre;
  }

  Future<void> _submit() async {
    final isValid = _formKey.currentState!.validate();
    if (!isValid) return;

    if (_selectedVehicle == null) {
      _showMessage('Selecciona un vehículo.', isError: true);
      return;
    }

    final coordinates = _resolveCoordinates();
    if (coordinates == null) {
      _showMessage('Selecciona la ubicación del incidente.', isError: true);
      return;
    }

    final description = _descController.text.trim();
    if (description.length < 10) {
      _showMessage('Describe el problema con más detalle.', isError: true);
      return;
    }

    if (_selectedSpecialty == null) {
      _showMessage(
        'Selecciona una sospecha inicial del problema.',
        isError: true,
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      final result =
          await ref.read(incidentSubmitProvider.notifier).submitIncident(
                vehicleId: _selectedVehicle!.idVehiculo,
                latitud: coordinates.latitud,
                longitud: coordinates.longitud,
                descripcionCliente: description,
                specialtyId: _selectedSpecialty!.idEspecialidad,
                images: _selectedImages,
              );

      if (mounted) {
        context.go(AppRoutes.incidentReported, extra: result);
      }
    } catch (e) {
      if (e is ApiException) {
        String message;
        if (e.statusCode == 400 || e.statusCode == 422) {
          message = 'Revisa los datos del reporte.';
        } else if (e.statusCode == 401 || e.statusCode == 403) {
          message = 'Tu sesión expiró. Inicia sesión nuevamente.';
        } else if (e.statusCode == 404) {
          message = 'No se encontró el vehículo seleccionado.';
        } else if (e.statusCode == 409) {
          message = 'No se pudo registrar el incidente en este momento.';
        } else if (e.statusCode != null && e.statusCode! >= 500) {
          message =
              'No se pudo enviar el reporte por un problema del servidor.';
        } else {
          message =
              'No se pudo conectar con el servidor. Revisa tu conexión.';
        }
        _showMessage(message, isError: true);
      } else {
        _showMessage(
          'No se pudo conectar con el servidor. Revisa tu conexión.',
          isError: true,
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final profileState = ref.watch(profileControllerProvider);
    final specialtiesState = ref.watch(specialtiesProvider);

    return AppPageScaffold(
      label: 'AUXILIO VIAL',
      title: 'Reportar incidente',
      subtitle: 'Cuéntanos qué ocurrió para iniciar la asistencia.',
      actions: IconButton(
        tooltip: 'Volver',
        icon: const Icon(Icons.arrow_back_rounded),
        onPressed: () {
          if (Navigator.of(context).canPop()) {
            context.pop();
          } else {
            context.go(AppRoutes.clientHome);
          }
        },
      ),
      child: Form(
        key: _formKey,
        child: ListView(
          children: [
            const _SectionLabel(title: 'Vehículo'),
            const SizedBox(height: 12),
            profileState.when(
              loading: () => const AppCard(
                child: Center(child: Text('Cargando tus vehículos...')),
              ),
              error: (_, __) => AppCard(
                child: Column(
                  children: [
                    const Text('No se pudieron cargar tus vehículos.'),
                    const SizedBox(height: 8),
                    OutlinedButton(
                      onPressed: () =>
                          ref.read(profileControllerProvider.notifier).refresh(),
                      child: const Text('Reintentar'),
                    ),
                  ],
                ),
              ),
              data: (profile) {
                if (profile.vehicles.isEmpty) {
                  return AppCard(
                    child: Column(
                      children: [
                        Icon(
                          Icons.directions_car_outlined,
                          size: 36,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Necesitas registrar un vehículo antes de reportar un incidente.',
                        ),
                        const SizedBox(height: 12),
                        OutlinedButton(
                          onPressed: () => context.push(AppRoutes.profile),
                          child: const Text('Gestionar vehículos'),
                        ),
                      ],
                    ),
                  );
                }

                return Column(
                  children: profile.vehicles.map((vehicle) {
                    final isSelected = _selectedVehicle?.idVehiculo ==
                        vehicle.idVehiculo;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: AppCard(
                        onTap: _isSubmitting
                            ? null
                            : () => setState(() => _selectedVehicle = vehicle),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 14,
                        ),
                        child: Row(
                          children: [
                            Icon(
                              isSelected
                                  ? Icons.radio_button_checked_rounded
                                  : Icons.radio_button_off_rounded,
                              color: isSelected
                                  ? theme.colorScheme.primary
                                  : theme.colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${vehicle.marcaNombre} ${vehicle.modeloNombre}',
                                    style: theme.textTheme.titleSmall,
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${vehicle.placa} • ${vehicle.anio} • ${vehicle.colorNombre}',
                                    style: theme.textTheme.bodySmall?.copyWith(
                                      color:
                                          theme.colorScheme.onSurfaceVariant,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
            const SizedBox(height: 20),
            const _SectionLabel(title: 'Ubicación del incidente'),
            const SizedBox(height: 12),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _LocationStatusCard(
                    state: _locationUiState,
                    message: _locationMessage,
                  ),
                  const SizedBox(height: 16),
                  AppPrimaryButton(
                    label: _isGettingLocation
                        ? 'Obteniendo ubicación...'
                        : 'Usar mi ubicación actual',
                    icon: Icons.my_location_rounded,
                    isLoading: _isGettingLocation,
                    onPressed: _isSubmitting || _isGettingLocation
                        ? null
                        : _useCurrentLocation,
                  ),
                  const SizedBox(height: 12),
                  Theme(
                    data: theme.copyWith(
                      dividerColor: Colors.transparent,
                    ),
                    child: ExpansionTile(
                      tilePadding: EdgeInsets.zero,
                      childrenPadding: EdgeInsets.zero,
                      title: const Text('Ingresar ubicación manualmente'),
                      initiallyExpanded: _showManualLocation,
                      onExpansionChanged: (expanded) {
                        setState(() {
                          _showManualLocation = expanded;
                        });
                      },
                      children: [
                        const SizedBox(height: 8),
                        TextFormField(
                          controller: _latController,
                          decoration: const InputDecoration(
                            labelText: 'Latitud',
                            hintText: 'Ej: -17.7833',
                            prefixIcon: Icon(Icons.my_location_outlined),
                          ),
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          enabled: !_isSubmitting,
                          onChanged: (_) => _syncManualLocation(),
                          validator: _validateManualLatitude,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _lonController,
                          decoration: const InputDecoration(
                            labelText: 'Longitud',
                            hintText: 'Ej: -63.1821',
                            prefixIcon: Icon(Icons.pin_drop_outlined),
                          ),
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          enabled: !_isSubmitting,
                          onChanged: (_) => _syncManualLocation(),
                          validator: _validateManualLongitude,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            const _SectionLabel(title: 'Descripción'),
            const SizedBox(height: 8),
            Text(
              'Describe qué pasó, qué ruido escuchaste o qué dejó de funcionar.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            AppCard(
              child: TextFormField(
                controller: _descController,
                decoration: const InputDecoration(
                  labelText: 'Descripción del problema',
                  alignLabelWithHint: true,
                ),
                maxLines: 4,
                maxLength: 2000,
                enabled: !_isSubmitting,
                validator: (value) {
                  final normalized = value?.trim() ?? '';
                  if (normalized.isEmpty) return 'Ingresa una descripción';
                  if (normalized.length < 10) {
                    return 'Mínimo 10 caracteres';
                  }
                  return null;
                },
              ),
            ),
            const SizedBox(height: 20),
            const _SectionLabel(title: 'Sospecha inicial'),
            const SizedBox(height: 8),
            Text(
              'Elige lo que más se parece al problema. Si no estás seguro, selecciona diagnóstico general.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            specialtiesState.when(
              loading: () => const AppCard(
                child: Center(child: Text('Cargando opciones...')),
              ),
              error: (_, __) => AppCard(
                child: Column(
                  children: [
                    const Text('No se pudieron cargar los tipos de falla.'),
                    const SizedBox(height: 8),
                    OutlinedButton(
                      onPressed: () =>
                          ref.read(specialtiesProvider.notifier).load(),
                      child: const Text('Reintentar'),
                    ),
                  ],
                ),
              ),
              data: (specialties) {
                final sorted = _sortSpecialties(specialties);
                if (sorted.isEmpty) {
                  return const AppCard(
                    child: Text(
                      'No hay opciones de sospecha inicial disponibles. Intenta más tarde.',
                    ),
                  );
                }

                return Column(
                  children: sorted.map((specialty) {
                    final isSelected = _selectedSpecialty?.idEspecialidad ==
                        specialty.idEspecialidad;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: AppCard(
                        onTap: _isSubmitting
                            ? null
                            : () => setState(
                                  () => _selectedSpecialty = specialty,
                                ),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 14,
                        ),
                        child: Row(
                          children: [
                            Icon(
                              isSelected
                                  ? Icons.radio_button_checked_rounded
                                  : Icons.radio_button_off_rounded,
                              color: isSelected
                                  ? theme.colorScheme.primary
                                  : theme.colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _specialtyDisplayName(specialty),
                                    style: theme.textTheme.titleSmall,
                                  ),
                                  if (specialty.descripcion != null &&
                                      specialty.descripcion!.isNotEmpty) ...[
                                    const SizedBox(height: 2),
                                    Text(
                                      specialty.descripcion!,
                                      style: theme.textTheme.bodySmall
                                          ?.copyWith(
                                        color:
                                            theme.colorScheme.onSurfaceVariant,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
            const SizedBox(height: 20),
            const _SectionLabel(title: 'Evidencias opcionales'),
            const SizedBox(height: 8),
            Text(
              'Agrega fotos si ayudan a mostrar la falla, el tablero o la llanta.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AppPrimaryButton(
                    label: _isPickingImages ? 'Abriendo galería...' : 'Agregar fotos',
                    icon: Icons.add_a_photo_outlined,
                    isLoading: _isPickingImages,
                    onPressed: _isSubmitting || _isPickingImages
                        ? null
                        : _pickImages,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    '${_selectedImages.length} de 5 foto(s) seleccionadas.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  if (_selectedImages.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _selectedImages.map((image) {
                        return Chip(
                          label: Text(
                            image.name,
                            overflow: TextOverflow.ellipsis,
                          ),
                          onDeleted: _isSubmitting
                              ? null
                              : () => _removeImage(image),
                        );
                      }).toList(),
                    ),
                  ],
                  const SizedBox(height: 12),
                  Text(
                    'El audio se agregará en una etapa posterior.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            AppPrimaryButton(
              label: _isSubmitting ? 'Enviando reporte...' : 'Enviar reporte',
              icon: Icons.send_rounded,
              isLoading: _isSubmitting,
              onPressed: _isSubmitting ? null : _submit,
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
    );
  }
}

class _LocationStatusCard extends StatelessWidget {
  const _LocationStatusCard({
    required this.state,
    required this.message,
  });

  final _LocationUiState state;
  final String message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final (icon, title, color) = switch (state) {
      _LocationUiState.pending => (
          Icons.location_searching_rounded,
          'Ubicación pendiente',
          theme.colorScheme.primary,
        ),
      _LocationUiState.success => (
          Icons.check_circle_outline_rounded,
          'Ubicación detectada',
          Colors.green.shade600,
        ),
      _LocationUiState.error => (
          Icons.error_outline_rounded,
          'No se pudo obtener ubicación',
          theme.colorScheme.error,
        ),
    };

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.16)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.titleSmall?.copyWith(color: color),
                ),
                const SizedBox(height: 4),
                Text(
                  message,
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
