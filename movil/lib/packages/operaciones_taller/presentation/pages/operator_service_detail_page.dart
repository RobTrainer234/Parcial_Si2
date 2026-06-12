import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
  Timer? _refreshTimer;
  bool _isSubmitting = false;
  bool _isSendingLocation = false;
  bool _isAcknowledgingProfile = false;
  bool _isOpeningMaps = false;
  bool _showServiceInfo = true;
  bool _showDiagnosis = false;
  bool _showTimeline = true;
  String? _previousState;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(const Duration(minutes: 1), (_) {
      if (!mounted) return;
      ref
          .read(operatorServiceDetailProvider(widget.serviceId).notifier)
          .refresh();
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

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

  Color _stateColor(String? state) {
    switch (state) {
      case 'ASIGNADO':
        return Colors.blue;
      case 'EN_CAMINO':
        return Colors.indigo;
      case 'EN_SITIO':
        return Colors.green;
      case 'EN_DIAGNOSTICO_FISICO':
      case 'EN_REPARACION':
        return Colors.deepPurple;
      case 'COMPLETADO_PENDIENTE_CONFIRMACION':
        return Colors.teal;
      case 'FINALIZADO_PENDIENTE_PAGO':
        return Colors.amber.shade700;
      case 'PAGADO':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(operatorServiceDetailProvider(widget.serviceId));

    return AppPageScaffold(
      label: 'OPERARIO',
      title: 'Detalle del servicio',
      subtitle: 'Gestiona la asistencia asignada.',
      leading: IconButton(
        tooltip: 'Volver',
        onPressed: () {
          if (context.canPop()) {
            context.pop();
          } else {
            context.go(AppRoutes.operatorHome);
          }
        },
        icon: const Icon(Icons.arrow_back_rounded),
      ),
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: () => ref
            .read(operatorServiceDetailProvider(widget.serviceId).notifier)
            .refresh(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      padding: EdgeInsets.zero,
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
          final arrived = navigation?.hasArrived ?? false;
          final canSendLocation = _canSendLocation(detail.serviceState);
          final nextActionLabel = _nextActionLabel(detail.serviceState);
          final needsProfileAcknowledgement =
              detail.serviceState == 'ASIGNADO' &&
                  progress != null &&
                  !(navigation?.profileAcknowledged ??
                      progress.profileAcknowledged);
          final incidentLatitud =
              navigation?.destinationLatitud ?? detail.latitud;
          final incidentLongitud =
              navigation?.destinationLongitud ?? detail.longitud;
          final operarioLatitud = navigation?.lastKnownLatitud;
          final operarioLongitud = navigation?.lastKnownLongitud;
          final lastLocationAt = navigation?.lastKnownAt;
          final isClosedOperationally =
              _isClosedOperationalState(detail.serviceState);

          final currentState = detail.serviceState;
          if (currentState != _previousState && _previousState != null) {
            HapticFeedback.mediumImpact();
            SystemSound.play(SystemSoundType.alert);
          }
          _previousState = currentState;

          return RefreshIndicator(
            onRefresh: () => ref
                .read(operatorServiceDetailProvider(widget.serviceId).notifier)
                .refresh(),
            child: ListView(
              children: [
                SizedBox(
                  height: 380,
                  child: Stack(
                    children: [
                      OperatorNavigationMap(
                        incidentLatitud: incidentLatitud,
                        incidentLongitud: incidentLongitud,
                        operarioLatitud: operarioLatitud,
                        operarioLongitud: operarioLongitud,
                        lastLocationAt: lastLocationAt,
                        routePoints: navigation?.routePoints,
                        routeDistanceMeters: navigation?.routeDistanceMeters,
                        routeDurationSeconds: navigation?.routeDurationSeconds,
                        hasArrived: arrived,
                      ),
                      if (navigation?.routeDistanceMeters != null ||
                          navigation?.routeDurationSeconds != null)
                        Positioned(
                          left: 16,
                          right: 16,
                          bottom: 16,
                          child: Material(
                            elevation: 6,
                            borderRadius: BorderRadius.circular(16),
                            color: Colors.white,
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 18,
                                vertical: 14,
                              ),
                              child: Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(10),
                                    decoration: BoxDecoration(
                                      color: Colors.blue.shade50,
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Icon(
                                      Icons.route,
                                      color: Colors.blue.shade700,
                                      size: 24,
                                    ),
                                  ),
                                  const SizedBox(width: 14),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        if (navigation?.routeDurationSeconds !=
                                            null)
                                          Text(
                                            _formatDuration(
                                              navigation!.routeDurationSeconds!,
                                            ),
                                            style: theme.textTheme.titleLarge
                                                ?.copyWith(
                                              fontWeight: FontWeight.w700,
                                              color:
                                                  theme.colorScheme.onSurface,
                                            ),
                                          ),
                                        if (navigation?.routeDistanceMeters !=
                                            null)
                                          Text(
                                            '${(navigation!.routeDistanceMeters! / 1000).toStringAsFixed(1)} km de distancia',
                                            style: theme.textTheme.bodySmall
                                                ?.copyWith(
                                              color: theme.colorScheme
                                                  .onSurfaceVariant,
                                            ),
                                          ),
                                      ],
                                    ),
                                  ),
                                  if (navigation?.currentDistanceMeters != null)
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 10,
                                        vertical: 6,
                                      ),
                                      decoration: BoxDecoration(
                                        color: Colors.green.shade50,
                                        borderRadius:
                                            BorderRadius.circular(20),
                                      ),
                                      child: Text(
                                        '${(navigation!.currentDistanceMeters! / 1000).toStringAsFixed(1)} km restantes',
                                        style: TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.w600,
                                          color: Colors.green.shade700,
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: _StatusCard(
                    stateColor: _stateColor(detail.serviceState),
                    serviceState: detail.serviceState,
                    workshopName: detail.workshopName,
                    arrived: arrived,
                    hasNavigation: navigation != null,
                  ),
                ),
                if (arrived) ...[
                  const SizedBox(height: 12),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: _ArrivalCelebration(
                      isOperator: true,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        InkWell(
                          onTap: () =>
                              setState(() => _showServiceInfo = !_showServiceInfo),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                Icon(
                                  Icons.description_outlined,
                                  size: 20,
                                  color: theme.colorScheme.primary,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    'Informacion del servicio',
                                    style: theme.textTheme.titleSmall,
                                  ),
                                ),
                                Icon(
                                  _showServiceInfo
                                      ? Icons.expand_less
                                      : Icons.expand_more,
                                  size: 20,
                                  color: theme.colorScheme.onSurfaceVariant,
                                ),
                              ],
                            ),
                          ),
                        ),
                        if (_showServiceInfo) ...[
                          const Divider(height: 16),
                          _InfoRow(
                            label: 'Estado del incidente',
                            value: localizeStatusLabel(detail.incidentState),
                          ),
                          if (detail.clientReportedSpecialty != null)
                            _InfoRow(
                              label: 'Especialidad reportada',
                              value: localizeSpecialtyLabel(
                                  detail.clientReportedSpecialty!),
                            ),
                          if (detail.detectedSpecialty != null)
                            _InfoRow(
                              label: 'Especialidad detectada',
                              value: localizeSpecialtyLabel(
                                  detail.detectedSpecialty!),
                            ),
                          if (detail.severity != null)
                            _InfoRow(
                              label: 'Severidad',
                              value: localizeStatusLabel(detail.severity!),
                            ),
                          if (detail.requiresTow != null)
                            _InfoRow(
                              label: 'Requiere grua',
                              value: detail.requiresTow! ? 'Si' : 'No',
                            ),
                          _InfoRow(
                            label: 'Evidencias',
                            value:
                                '${detail.evidenceSummary.images} imagen(es), ${detail.evidenceSummary.audio} audio(s)',
                          ),
                          if (detail.audioTranscript != null &&
                              detail.audioTranscript!.trim().isNotEmpty)
                            _InfoRow(
                              label: 'Transcripcion de audio',
                              value: detail.audioTranscript!,
                            ),
                          if (detail.audioSummary != null &&
                              detail.audioSummary!.trim().isNotEmpty)
                            _InfoRow(
                              label: 'Resumen de audio',
                              value: detail.audioSummary!,
                            ),
                          if (detail.audioAnalysisType ==
                              'MECHANICAL_SOUND_EXPERIMENTAL')
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                'El audio no contiene voz clara. El analisis por sonido mecanico es experimental.',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: Colors.orange.shade700,
                                ),
                              ),
                            ),
                          if (detail.requiresManualReview)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                'La IA no tiene certeza completa. El taller realizara diagnostico fisico.',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: Colors.orange.shade700,
                                ),
                              ),
                            ),
                        ],
                      ],
                    ),
                  ),
                ),
                if (detail.aiSummary != null &&
                    detail.aiSummary!.trim().isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          InkWell(
                            onTap: () => setState(
                                () => _showDiagnosis = !_showDiagnosis),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.psychology_outlined,
                                    size: 20,
                                    color: theme.colorScheme.primary,
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      'Diagnostico IA',
                                      style: theme.textTheme.titleSmall,
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: detail.confidence != null &&
                                              detail.confidence! >= 70
                                          ? Colors.green.shade50
                                          : Colors.orange.shade50,
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Text(
                                      '${detail.confidence?.toStringAsFixed(0) ?? '?'}%',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: detail.confidence != null &&
                                                detail.confidence! >= 70
                                            ? Colors.green.shade700
                                            : Colors.orange.shade700,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 4),
                                  Icon(
                                    _showDiagnosis
                                        ? Icons.expand_less
                                        : Icons.expand_more,
                                    size: 20,
                                    color: theme.colorScheme.onSurfaceVariant,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          if (_showDiagnosis) ...[
                            const Divider(height: 16),
                            _InfoRow(
                              label: 'Resumen',
                              value: detail.aiSummary!,
                            ),
                            if (detail.specificDiagnosis != null &&
                                detail.specificDiagnosis!.trim().isNotEmpty)
                              _InfoRow(
                                label: 'Diagnostico especifico',
                                value: detail.specificDiagnosis!,
                              ),
                            if (detail.suggestedService != null &&
                                detail.suggestedService!.trim().isNotEmpty)
                              _InfoRow(
                                label: 'Servicio sugerido',
                                value: detail.suggestedService!,
                              ),
                            if (detail.customerRecommendation != null &&
                                detail.customerRecommendation!
                                    .trim().isNotEmpty)
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
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
                if (progress != null && progress.timeline.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: _TimelineCard(
                      timeline: progress.timeline,
                      showTimeline: _showTimeline,
                      onToggle: () =>
                          setState(() => _showTimeline = !_showTimeline),
                    ),
                  ),
                ],
                if (canSendLocation) ...[
                  const SizedBox(height: 12),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _isSendingLocation
                                ? null
                                : _sendCurrentLocation,
                            icon: _isSendingLocation
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.my_location, size: 18),
                            label: Text(
                              _isSendingLocation
                                  ? 'Enviando...'
                                  : 'Enviar ubicacion',
                            ),
                          ),
                        ),
                        if (incidentLatitud != null &&
                            incidentLongitud != null) ...[
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _isOpeningMaps
                                  ? null
                                  : () => _openRouteInMaps(
                                        incidentLatitud,
                                        incidentLongitud,
                                      ),
                              icon: _isOpeningMaps
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Icon(Icons.map_outlined, size: 18),
                              label: Text(
                                _isOpeningMaps
                                    ? 'Abriendo...'
                                    : 'Abrir en maps',
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
                if (needsProfileAcknowledgement) ...[
                  const SizedBox(height: 12),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: _ProfileBanner(
                      isLoading: _isAcknowledgingProfile,
                      onAcknowledge: _acknowledgeProfile,
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                if (isClosedOperationally)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: AppCard(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          children: [
                            Icon(
                              Icons.check_circle,
                              color: Colors.green.shade600,
                              size: 24,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                'Servicio cerrado operativamente.',
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                if (nextActionLabel != null) ...[
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: AppPrimaryButton(
                      label: nextActionLabel,
                      isLoading: _isSubmitting,
                      onPressed:
                          _isSubmitting || needsProfileAcknowledgement
                              ? null
                              : () => _runMainAction(viewModel),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                SizedBox(
                  width: double.infinity,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
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
                ),
                const SizedBox(height: 24),
              ],
            ),
          );
        },
      ),
    );
  }
}

String _formatDuration(double seconds) {
  final totalMinutes = (seconds / 60).round();
  if (totalMinutes < 60) return '$totalMinutes min';
  final hours = totalMinutes ~/ 60;
  final minutes = totalMinutes % 60;
  if (minutes == 0) return '${hours}h';
  return '${hours}h ${minutes}min';
}

class _StatusCard extends StatelessWidget {
  final Color stateColor;
  final String serviceState;
  final String? workshopName;
  final bool arrived;
  final bool hasNavigation;

  const _StatusCard({
    required this.stateColor,
    required this.serviceState,
    this.workshopName,
    required this.arrived,
    required this.hasNavigation,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: 6,
            decoration: BoxDecoration(
              color: stateColor,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(16),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(18),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: stateColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    arrived
                        ? Icons.check_circle_outline
                        : hasNavigation
                            ? Icons.navigation
                            : Icons.pending_outlined,
                    color: stateColor,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: stateColor.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              _friendlyOperatorState(serviceState),
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: stateColor,
                              ),
                            ),
                          ),
                          if (arrived) ...[
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.green.shade50,
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Text(
                                'Llegaste',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.green.shade700,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                      if (workshopName != null) ...[
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Icon(
                              Icons.store_outlined,
                              size: 16,
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              workshopName!,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ArrivalCelebration extends StatelessWidget {
  final bool isOperator;
  const _ArrivalCelebration({required this.isOperator});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.green.shade500, Colors.green.shade700],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.green.shade400.withValues(alpha: 0.3),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(
              isOperator ? Icons.location_on : Icons.celebration_outlined,
              color: Colors.white,
              size: 32,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isOperator
                      ? '¡Llegaste al lugar!'
                      : '¡El operario llego!',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  isOperator
                      ? 'Inicia el diagnostico fisico del vehiculo.'
                      : 'Esta en el lugar del incidente para atenderte.',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.9),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TimelineCard extends StatelessWidget {
  final List<OperatorProgressTimelineItemModel> timeline;
  final bool showTimeline;
  final VoidCallback onToggle;

  const _TimelineCard({
    required this.timeline,
    required this.showTimeline,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: onToggle,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Icon(
                    Icons.timeline,
                    size: 20,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Historial operativo',
                      style: theme.textTheme.titleSmall,
                    ),
                  ),
                  Text(
                    '${timeline.length} eventos',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    showTimeline ? Icons.expand_less : Icons.expand_more,
                    size: 20,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ],
              ),
            ),
          ),
          if (showTimeline) ...[
            const Divider(height: 16),
            ...List.generate(timeline.length, (index) {
              final item = timeline[index];
              final isLast = index == timeline.length - 1;
              return _TimelineItem(
                item: item,
                isLast: isLast,
                isFirst: index == 0,
              );
            }),
          ],
        ],
      ),
    );
  }
}

class _TimelineItem extends StatelessWidget {
  final OperatorProgressTimelineItemModel item;
  final bool isLast;
  final bool isFirst;

  const _TimelineItem({
    required this.item,
    required this.isLast,
    required this.isFirst,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final icon = _timelineIcon(item.action);
    final color = _timelineColor(item.action);

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 40,
            child: Column(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(icon, size: 16, color: color),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: color.withValues(alpha: 0.2),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (item.timestamp != null)
                    Text(
                      _formatDate(item.timestamp!),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                        fontSize: 11,
                      ),
                    ),
                  const SizedBox(height: 2),
                  Text(
                    _humanizeTimelineAction(item.action),
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (item.newState != null)
                    Text(
                      'Estado: ${_friendlyOperatorState(item.newState!)}',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  if (item.observation != null &&
                      item.observation!.trim().isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        item.observation!,
                        style: theme.textTheme.bodySmall,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

IconData _timelineIcon(String action) {
  switch (action) {
    case 'NAVEGACION_INICIADA':
      return Icons.navigation;
    case 'OPERARIO_EN_SITIO':
      return Icons.location_on;
    case 'SERVICIO_ESTADO_ACTUALIZADO':
      return Icons.update;
    default:
      return Icons.circle;
  }
}

Color _timelineColor(String action) {
  switch (action) {
    case 'NAVEGACION_INICIADA':
      return Colors.blue;
    case 'OPERARIO_EN_SITIO':
      return Colors.green;
    default:
      return Colors.grey;
  }
}

class _ProfileBanner extends StatelessWidget {
  final bool isLoading;
  final VoidCallback onAcknowledge;

  const _ProfileBanner({
    required this.isLoading,
    required this.onAcknowledge,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.amber.shade200),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline, color: Colors.amber.shade800, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Antes de iniciar la ruta, revisa el perfil tecnico.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: Colors.amber.shade900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: isLoading ? null : onAcknowledge,
              icon: isLoading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.visibility, size: 18),
              label: Text(
                isLoading
                    ? 'Guardando...'
                    : 'Marcar perfil como revisado',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RepairCompletionDialog extends StatefulWidget {
  const _RepairCompletionDialog();

  @override
  State<_RepairCompletionDialog> createState() =>
      _RepairCompletionDialogState();
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
      title: const Text('Finalizar atencion'),
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

String _formatDate(DateTime value) {
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
