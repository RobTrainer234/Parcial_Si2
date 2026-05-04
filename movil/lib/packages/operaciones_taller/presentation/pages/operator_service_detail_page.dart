import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/utils/user_facing_text.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_error_view.dart';
import '../../../../core/widgets/app_loading.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/models/operator_progress_response_model.dart';
import '../controllers/operator_service_detail_controller.dart';
import '../widgets/operator_navigation_map.dart';

class OperatorServiceDetailPage extends ConsumerStatefulWidget {
  const OperatorServiceDetailPage({
    super.key,
    required this.serviceId,
  });

  final int serviceId;

  @override
  ConsumerState<OperatorServiceDetailPage> createState() =>
      _OperatorServiceDetailPageState();
}

class _OperatorServiceDetailPageState
    extends ConsumerState<OperatorServiceDetailPage> {
  bool _isSubmitting = false;
  bool _isSendingLocation = false;
  bool _isAcknowledgingProfile = false;
  bool _isOpeningMaps = false;

  Future<void> _runMainAction(
    OperatorServiceDetailViewModel viewModel,
  ) async {
    final currentState = viewModel.detail.serviceState;
    setState(() {
      _isSubmitting = true;
    });

    try {
      late final OperatorProgressResponseModel response;
      switch (currentState) {
        case 'ASIGNADO':
          final position = await _getCurrentPosition();
          response = await ref
              .read(operatorServiceDetailProvider(widget.serviceId).notifier)
              .startNavigation(
                latitud: position.latitude,
                longitud: position.longitude,
                accuracyMeters:
                    position.accuracy >= 0 ? position.accuracy : null,
                speedMps: position.speed >= 0 ? position.speed : null,
              );
          break;
        case 'EN_CAMINO':
          final position = await _getCurrentPosition();
          await ref
              .read(operatorServiceDetailProvider(widget.serviceId).notifier)
              .updateLocation(
                latitud: position.latitude,
                longitud: position.longitude,
                accuracyMeters:
                    position.accuracy >= 0 ? position.accuracy : null,
                heading: position.heading >= 0 ? position.heading : null,
                speedMps: position.speed >= 0 ? position.speed : null,
                deviceTimestamp: DateTime.now().toUtc(),
              );
          response = await ref
              .read(operatorServiceDetailProvider(widget.serviceId).notifier)
              .updateProgress(newState: 'EN_SITIO');
          break;
        case 'EN_SITIO':
          response = await ref
              .read(operatorServiceDetailProvider(widget.serviceId).notifier)
              .updateProgress(newState: 'EN_DIAGNOSTICO_FISICO');
          break;
        case 'EN_DIAGNOSTICO_FISICO':
          response = await ref
              .read(operatorServiceDetailProvider(widget.serviceId).notifier)
              .updateProgress(newState: 'EN_REPARACION');
          break;
        case 'EN_REPARACION':
          final payload = await showDialog<String>(
            context: context,
            builder: (context) => const _RepairCompletionDialog(),
          );
          if (payload == null) {
            return;
          }
          response = await ref
              .read(operatorServiceDetailProvider(widget.serviceId).notifier)
              .completeRepair(
                actionPerformed: payload.trim().isEmpty
                    ? 'Atencion completada por el operario.'
                    : payload.trim(),
                observations: payload.trim().isEmpty ? null : payload.trim(),
              );
          break;
        default:
          return;
      }

      final localizedMessage = localizeBackendMessage(response.message);
      _showSnack(
        localizedMessage.isNotEmpty && localizedMessage != response.message
            ? localizedMessage
            : currentState == 'EN_REPARACION'
                ? 'Atencion finalizada. Esperando confirmacion del cliente.'
                : 'Servicio actualizado correctamente.',
      );
    } catch (error) {
      _showSnack(_mapOperatorActionError(error));
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  Future<void> _sendCurrentLocation() async {
    setState(() {
      _isSendingLocation = true;
    });

    try {
      final position = await _getCurrentPosition();
      final response = await ref
          .read(operatorServiceDetailProvider(widget.serviceId).notifier)
          .updateLocation(
            latitud: position.latitude,
            longitud: position.longitude,
            accuracyMeters: position.accuracy >= 0 ? position.accuracy : null,
            heading: position.heading >= 0 ? position.heading : null,
            speedMps: position.speed >= 0 ? position.speed : null,
            deviceTimestamp: DateTime.now().toUtc(),
          );
      final localizedMessage = localizeBackendMessage(response.message);
      _showSnack(
        localizedMessage.isNotEmpty && localizedMessage != response.message
            ? localizedMessage
            : 'Ubicacion enviada correctamente.',
      );
    } catch (error) {
      _showSnack(_mapOperatorActionError(error));
    } finally {
      if (mounted) {
        setState(() {
          _isSendingLocation = false;
        });
      }
    }
  }

  Future<void> _acknowledgeProfile() async {
    setState(() {
      _isAcknowledgingProfile = true;
    });

    try {
      await ref
          .read(operatorServiceDetailProvider(widget.serviceId).notifier)
          .acknowledgeProfile();
      _showSnack('Perfil tecnico marcado como revisado.');
    } catch (error) {
      _showSnack(_mapOperatorActionError(error));
    } finally {
      if (mounted) {
        setState(() {
          _isAcknowledgingProfile = false;
        });
      }
    }
  }

  Future<void> _openRouteInMaps(double latitud, double longitud) async {
    setState(() {
      _isOpeningMaps = true;
    });

    try {
      final uri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&destination=$latitud,$longitud',
      );
      final opened = await launchUrl(uri);
      if (!opened) {
        throw const _OpenMapsException(
          'No se pudo abrir la aplicacion de mapas.',
        );
      }
    } catch (_) {
      _showSnack('No se pudo abrir la aplicacion de mapas.');
    } finally {
      if (mounted) {
        setState(() {
          _isOpeningMaps = false;
        });
      }
    }
  }

  Future<Position> _getCurrentPosition() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw const _FriendlyLocationException(
        'No se pudo obtener tu ubicacion. Revisa los permisos del navegador o del dispositivo.',
      );
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      throw const _FriendlyLocationException(
        'No se pudo obtener tu ubicacion. Revisa los permisos del navegador o del dispositivo.',
      );
    }

    return Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 15),
      ),
    );
  }

  void _showSnack(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(operatorServiceDetailProvider(widget.serviceId));

    return AppPageScaffold(
      label: 'OPERARIO',
      title: 'Detalle del servicio',
      subtitle: 'Revisa el diagnostico y avanza la asistencia asignada.',
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: () => ref
            .read(operatorServiceDetailProvider(widget.serviceId).notifier)
            .refresh(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      child: state.when(
        loading: () => const AppLoading(message: 'Cargando servicio...'),
        error: (error, _) {
          if (_isClosedOperationalError(error)) {
            return const _ClosedServiceView();
          }
          return AppErrorView(
            message: _mapOperatorDetailError(error),
            onRetry: () => ref
                .read(operatorServiceDetailProvider(widget.serviceId).notifier)
                .refresh(),
          );
        },
        data: (viewModel) {
          final detail = viewModel.detail;
          final progress = viewModel.progress;
          final navigation = viewModel.navigationStatus;
          final canSendLocation = _canSendLocation(detail.serviceState);
          final nextActionLabel = _nextActionLabel(detail.serviceState);
          final needsProfileAcknowledgement =
              detail.serviceState == 'ASIGNADO' &&
              progress != null &&
              !(navigation?.profileAcknowledged ?? progress.profileAcknowledged);
          final incidentLatitud = navigation?.destinationLatitud ?? detail.latitud;
          final incidentLongitud =
              navigation?.destinationLongitud ?? detail.longitud;
          final operarioLatitud = navigation?.lastKnownLatitud;
          final operarioLongitud = navigation?.lastKnownLongitud;
          final lastLocationAt = navigation?.lastKnownAt;
          final isClosedOperationally =
              _isClosedOperationalState(detail.serviceState);

          return RefreshIndicator(
            onRefresh: () => ref
                .read(operatorServiceDetailProvider(widget.serviceId).notifier)
                .refresh(),
            child: ListView(
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Servicio de auxilio',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      _InfoRow(
                        label: 'Estado del servicio',
                        value: _friendlyOperatorState(detail.serviceState),
                      ),
                      _InfoRow(
                        label: 'Estado del incidente',
                        value: localizeStatusLabel(detail.incidentState),
                      ),
                      if (detail.workshopName != null)
                        _InfoRow(
                          label: 'Taller',
                          value: detail.workshopName!,
                        ),
                      if (detail.clientReportedSpecialty != null)
                        _InfoRow(
                          label: 'Especialidad reportada',
                          value:
                              localizeSpecialtyLabel(detail.clientReportedSpecialty),
                        ),
                      if (detail.detectedSpecialty != null)
                        _InfoRow(
                          label: 'Especialidad detectada',
                          value:
                              localizeSpecialtyLabel(detail.detectedSpecialty),
                        ),
                      if (detail.severity != null)
                        _InfoRow(
                          label: 'Severidad',
                          value: localizeStatusLabel(detail.severity),
                        ),
                      if (detail.confidence != null)
                        _InfoRow(
                          label: 'Confianza IA',
                          value: '${detail.confidence!.toStringAsFixed(0)}%',
                        ),
                      if (detail.aiSummary != null &&
                          detail.aiSummary!.trim().isNotEmpty)
                        _InfoRow(
                          label: 'Resumen IA',
                          value: detail.aiSummary!,
                        ),
                      if (detail.specificDiagnosis != null &&
                          detail.specificDiagnosis!.trim().isNotEmpty)
                        _InfoRow(
                          label: 'Diagnóstico específico',
                          value: detail.specificDiagnosis!,
                        ),
                      if (detail.suggestedService != null &&
                          detail.suggestedService!.trim().isNotEmpty)
                        _InfoRow(
                          label: 'Servicio sugerido',
                          value: detail.suggestedService!,
                        ),
                      if (detail.customerRecommendation != null &&
                          detail.customerRecommendation!.trim().isNotEmpty)
                        _InfoRow(
                          label: 'Recomendacion para el cliente',
                          value: detail.customerRecommendation!,
                        ),
                      if (detail.operatorNotes != null &&
                          detail.operatorNotes!.trim().isNotEmpty)
                        _InfoRow(
                          label: 'Notas para el operario',
                          value: detail.operatorNotes!,
                        ),
                      _InfoRow(
                        label: 'Ubicacion del cliente',
                        value: _formatClientLocation(
                          incidentLatitud,
                          incidentLongitud,
                        ),
                      ),
                      if (detail.requiresTow != null)
                        _InfoRow(
                          label: 'Requiere grua',
                          value: detail.requiresTow! ? 'Si' : 'No',
                        ),
                      if (detail.observations != null &&
                          detail.observations!.trim().isNotEmpty)
                        _InfoRow(
                          label: 'Observaciones',
                          value: detail.observations!,
                        ),
                      if (_formatImageLabels(detail.imageLabels) != null)
                        _InfoRow(
                          label: 'Etiquetas de imagen',
                          value: _formatImageLabels(detail.imageLabels)!,
                        ),
                      if (detail.visualEvidenceTags.isNotEmpty)
                        _InfoRow(
                          label: 'Evidencias visuales',
                          value: detail.visualEvidenceTags.join(', '),
                        ),
                      if (detail.suggestedTools.isNotEmpty)
                        _InfoRow(
                          label: 'Herramientas sugeridas',
                          value: detail.suggestedTools.join(', '),
                        ),
                      if (detail.prequotationMin != null &&
                          detail.prequotationMax != null)
                        _InfoRow(
                          label: 'Pre-cotizacion',
                          value:
                              '${detail.prequotationCurrency ?? 'BOB'} ${detail.prequotationMin!.toStringAsFixed(2)} - ${detail.prequotationMax!.toStringAsFixed(2)}',
                        ),
                      _InfoRow(
                        label: 'Evidencias',
                        value:
                            '${detail.evidenceSummary.images} imagen(es), ${detail.evidenceSummary.audio} audio(s)',
                      ),
                      if (detail.requiresManualReview)
                        const Padding(
                          padding: EdgeInsets.only(top: 8),
                          child: Text(
                            'La IA no tiene certeza completa. El taller realizará diagnóstico físico.',
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                OperatorNavigationMap(
                  incidentLatitud: incidentLatitud,
                  incidentLongitud: incidentLongitud,
                  operarioLatitud: operarioLatitud,
                  operarioLongitud: operarioLongitud,
                  lastLocationAt: lastLocationAt,
                ),
                const SizedBox(height: 16),
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (incidentLatitud != null && incidentLongitud != null)
                        _InfoRow(
                          label: 'Ubicacion del incidente',
                          value:
                              '${incidentLatitud.toStringAsFixed(5)}, ${incidentLongitud.toStringAsFixed(5)}',
                        )
                      else
                        const Text(
                          'La ubicacion del incidente no esta disponible.',
                        ),
                      const SizedBox(height: 8),
                      if (operarioLatitud != null && operarioLongitud != null)
                        _InfoRow(
                          label: 'Tu ubicacion actual',
                          value:
                              '${operarioLatitud.toStringAsFixed(5)}, ${operarioLongitud.toStringAsFixed(5)}',
                        )
                      else
                        const Text(
                          'Envia tu ubicacion actual para iniciar el seguimiento.',
                        ),
                      if (lastLocationAt != null)
                        _InfoRow(
                          label: 'Ultima actualizacion',
                          value: _formatDate(lastLocationAt),
                        ),
                      if (navigation?.currentDistanceMeters != null)
                        _InfoRow(
                          label: 'Distancia al incidente',
                          value:
                              '${(navigation!.currentDistanceMeters! / 1000).toStringAsFixed(2)} km',
                        ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          OutlinedButton(
                            onPressed: canSendLocation && !_isSendingLocation
                                ? _sendCurrentLocation
                                : null,
                            child: Text(
                              _isSendingLocation
                                  ? 'Enviando ubicacion...'
                                  : 'Enviar mi ubicacion actual',
                            ),
                          ),
                          OutlinedButton(
                            onPressed: incidentLatitud != null &&
                                    incidentLongitud != null &&
                                    !_isOpeningMaps
                                ? () => _openRouteInMaps(
                                      incidentLatitud,
                                      incidentLongitud,
                                    )
                                : null,
                            child: Text(
                              _isOpeningMaps
                                  ? 'Abriendo ruta...'
                                  : 'Abrir ruta en mapas',
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                if (progress != null && progress.timeline.isNotEmpty)
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Historial operativo',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        ...progress.timeline.map(
                          (item) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _formatDate(item.timestamp),
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodySmall
                                      ?.copyWith(
                                        color: Theme.of(context)
                                            .colorScheme
                                            .onSurfaceVariant,
                                      ),
                                ),
                                const SizedBox(height: 4),
                                Text(_humanizeTimelineAction(item.action)),
                                if (item.newState != null)
                                  Text(
                                    'Estado: ${_friendlyOperatorState(item.newState!)}',
                                  ),
                                if (item.observation != null &&
                                    item.observation!.trim().isNotEmpty)
                                  Text(item.observation!),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                if (progress != null) const SizedBox(height: 16),
                if (needsProfileAcknowledgement)
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Antes de iniciar la ruta debes revisar el perfil tecnico del servicio.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton(
                            onPressed:
                                _isAcknowledgingProfile ? null : _acknowledgeProfile,
                            child: Text(
                              _isAcknowledgingProfile
                                  ? 'Guardando revision...'
                                  : 'Marcar perfil como revisado',
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                if (needsProfileAcknowledgement) const SizedBox(height: 16),
                if (isClosedOperationally)
                  const AppCard(
                    child: Text(
                      'El servicio ya fue cerrado operativamente.',
                    ),
                  ),
                if (isClosedOperationally) const SizedBox(height: 16),
                if (nextActionLabel != null)
                  AppPrimaryButton(
                    label: nextActionLabel,
                    isLoading: _isSubmitting,
                    onPressed: _isSubmitting || needsProfileAcknowledgement
                        ? null
                        : () => _runMainAction(viewModel),
                  ),
                if (nextActionLabel != null) const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: () {
                      if (context.canPop()) {
                        context.pop();
                      } else {
                        context.go(AppRoutes.operatorHome);
                      }
                    },
                    child: Text(
                      isClosedOperationally
                          ? 'Volver a servicios asignados'
                          : 'Volver',
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _RepairCompletionDialog extends StatefulWidget {
  const _RepairCompletionDialog();

  @override
  State<_RepairCompletionDialog> createState() => _RepairCompletionDialogState();
}

class _RepairCompletionDialogState extends State<_RepairCompletionDialog> {
  final _observationController = TextEditingController();

  @override
  void dispose() {
    _observationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('¿Finalizar atencion?'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'El cliente podra confirmar si el problema quedo resuelto.',
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _observationController,
              maxLength: 2000,
              minLines: 3,
              maxLines: 5,
              decoration: const InputDecoration(
                labelText: 'Observacion opcional',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: () {
            Navigator.of(context).pop(_observationController.text);
          },
          child: const Text('Finalizar'),
        ),
      ],
    );
  }
}

class _ClosedServiceView extends StatelessWidget {
  const _ClosedServiceView();

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Este servicio ya no esta disponible para operacion.',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              const Text(
                'Puede haber sido completado, pagado o cerrado.',
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => context.go(AppRoutes.operatorHome),
                  child: const Text('Volver a servicios asignados'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

bool _isClosedOperationalError(Object error) {
  if (error is ApiException && error.statusCode == 409) {
    return true;
  }
  return false;
}

String _mapOperatorDetailError(Object error) {
  if (error is ApiException) {
    final detail = _extractDetail(error);
    final localized = localizeBackendMessage(detail);
    if (localized.isNotEmpty && localized != detail) {
      return localized;
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesion expiro o no tienes permiso para esta accion.';
    }
    if (error.statusCode == 404) {
      return 'No se encontro el servicio asignado.';
    }
    if (error.statusCode == 409) {
      return 'Este servicio ya no esta disponible para operacion.';
    }
    if (error.statusCode == 422) {
      return 'Revisa los datos enviados.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo cargar el servicio.';
    }
  }
  return 'No se pudo conectar con el servidor.';
}

String _mapOperatorActionError(Object error) {
  if (error is _FriendlyLocationException) {
    return error.message;
  }
  if (error is _OpenMapsException) {
    return error.message;
  }
  if (error is ApiException) {
    final detail = _extractDetail(error);
    final localized = localizeBackendMessage(detail);
    if (localized.isNotEmpty && localized != detail) {
      return localized;
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesion expiro o no tienes permiso para esta accion.';
    }
    if (error.statusCode == 404) {
      return 'No se encontro el servicio asignado.';
    }
    if (error.statusCode == 409) {
      return 'El servicio no esta en un estado valido para esta accion.';
    }
    if (error.statusCode == 422 || error.statusCode == 400) {
      return 'Revisa los datos enviados.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo actualizar el servicio.';
    }
  }
  return 'No se pudo conectar con el servidor.';
}

String _extractDetail(ApiException error) {
  final details = error.details;
  if (details is Map<String, dynamic>) {
    final detail = details['detail'];
    if (detail is String) {
      return detail;
    }
  } else if (details is Map) {
    final detail = details['detail'];
    if (detail is String) {
      return detail;
    }
  }
  return '';
}

bool _canSendLocation(String state) {
  return {
    'ASIGNADO',
    'EN_CAMINO',
    'EN_SITIO',
    'EN_DIAGNOSTICO_FISICO',
    'EN_REPARACION',
  }.contains(state);
}

bool _isClosedOperationalState(String state) {
  return state == 'COMPLETADO_PENDIENTE_CONFIRMACION' ||
      state == 'FINALIZADO_PENDIENTE_PAGO' ||
      state == 'PAGADO';
}

String? _nextActionLabel(String state) {
  switch (state) {
    case 'ASIGNADO':
      return 'Iniciar ruta';
    case 'EN_CAMINO':
      return 'Llegue al lugar';
    case 'EN_SITIO':
      return 'Iniciar diagnostico fisico';
    case 'EN_DIAGNOSTICO_FISICO':
      return 'Iniciar reparacion';
    case 'EN_REPARACION':
      return 'Finalizar atencion';
    default:
      return null;
  }
}

String _friendlyOperatorState(String state) {
  switch (state) {
    case 'ASIGNADO':
      return 'Asignado';
    case 'EN_CAMINO':
      return 'En camino';
    case 'EN_SITIO':
      return 'En sitio';
    case 'EN_DIAGNOSTICO_FISICO':
      return 'Diagnostico fisico';
    case 'EN_REPARACION':
      return 'En reparacion';
    case 'COMPLETADO_PENDIENTE_CONFIRMACION':
      return 'Pendiente de confirmacion del cliente';
    case 'FINALIZADO_PENDIENTE_PAGO':
      return 'Pendiente de pago';
    case 'PAGADO':
      return 'Pagado';
    default:
      return localizeStatusLabel(state);
  }
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

String _humanizeTimelineAction(String action) {
  switch (action) {
    case 'NAVEGACION_INICIADA':
      return 'Navegacion iniciada';
    case 'OPERARIO_EN_SITIO':
      return 'Llegada al lugar';
    case 'SERVICIO_ESTADO_ACTUALIZADO':
      return 'Estado operativo actualizado';
    default:
      return localizeStatusLabel(action);
  }
}

String? _formatImageLabels(dynamic value) {
  if (value is List) {
    final labels = value
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList();
    return labels.isEmpty ? null : labels.join(', ');
  }
  if (value is Map) {
    final parts = <String>[];
    value.forEach((key, item) {
      final rendered = item?.toString().trim();
      if (rendered != null && rendered.isNotEmpty) {
        parts.add('$key: $rendered');
      }
    });
    return parts.isEmpty ? null : parts.join(', ');
  }
  if (value is String && value.trim().isNotEmpty) {
    return value.trim();
  }
  return null;
}

String _formatClientLocation(double? latitud, double? longitud) {
  if (latitud == null || longitud == null) {
    return 'Ubicacion del cliente no disponible';
  }
  return '${latitud.toStringAsFixed(5)}, ${longitud.toStringAsFixed(5)}';
}

class _FriendlyLocationException implements Exception {
  final String message;

  const _FriendlyLocationException(this.message);
}

class _OpenMapsException implements Exception {
  final String message;

  const _OpenMapsException(this.message);
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 4),
          Text(value),
        ],
      ),
    );
  }
}
