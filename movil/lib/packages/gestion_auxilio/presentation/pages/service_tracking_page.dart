import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/utils/user_facing_text.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_empty_view.dart';
import '../../../../core/widgets/app_error_view.dart';
import '../../../../core/widgets/app_loading.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../controllers/service_tracking_controller.dart';
import '../widgets/service_tracking_map.dart';

class ServiceTrackingPage extends ConsumerStatefulWidget {
  const ServiceTrackingPage({
    super.key,
    required this.serviceId,
  });

  final int serviceId;

  @override
  ConsumerState<ServiceTrackingPage> createState() =>
      _ServiceTrackingPageState();
}

class _ServiceTrackingPageState extends ConsumerState<ServiceTrackingPage> {
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (!mounted) {
        return;
      }
      ref
          .read(serviceTrackingProvider(widget.serviceId).notifier)
          .refreshSilently();
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(serviceTrackingProvider(widget.serviceId));

    return AppPageScaffold(
      label: 'SEGUIMIENTO',
      title: 'Seguimiento del servicio',
      subtitle: 'Consulta el avance de tu asistencia.',
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: () => ref
            .read(serviceTrackingProvider(widget.serviceId).notifier)
            .refresh(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      child: state.when(
        loading: () => const AppLoading(message: 'Cargando seguimiento...'),
        error: (error, _) => AppErrorView(
          message: _mapTrackingError(error),
          onRetry: () => ref
              .read(serviceTrackingProvider(widget.serviceId).notifier)
              .refresh(),
        ),
        data: (data) {
          final status = data.status;
          final validHistory = data.history
              .where(
                (point) => point.latitud != null && point.longitud != null,
              )
              .toList();
          final recentHistory = validHistory.length <= 5
              ? validHistory.reversed.toList()
              : validHistory.reversed.take(5).toList();

          return RefreshIndicator(
            onRefresh: () => ref
                .read(serviceTrackingProvider(widget.serviceId).notifier)
                .refresh(),
            child: ListView(
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Tu asistencia',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      _InfoRow(
                        label: 'Estado del servicio',
                        value: _friendlyServiceState(status.serviceState),
                      ),
                      if (status.lastLocationAt != null)
                        _InfoRow(
                          label: 'Ultima actualizacion',
                          value: _formatDate(status.lastLocationAt),
                        ),
                      if (status.currentDistanceMeters != null)
                        _InfoRow(
                          label: 'Distancia actual',
                          value:
                              '${(status.currentDistanceMeters! / 1000).toStringAsFixed(2)} km',
                        ),
                      if (status.etaText != null)
                        _InfoRow(
                          label: 'Llegada estimada',
                          value: status.etaText!,
                        ),
                      const SizedBox(height: 4),
                      Text(
                        _trackingMessage(status.serviceState, status),
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
                if (_shouldShowLifecycleSummary(status.serviceState)) ...[
                  const SizedBox(height: 16),
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _lifecycleSummaryTitle(status.serviceState),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(_lifecycleSummaryMessage(status.serviceState)),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                ServiceTrackingMap(
                  incidentLatitud: status.incidentLatitud,
                  incidentLongitud: status.incidentLongitud,
                  operarioLatitud: status.lastOperarioLatitud,
                  operarioLongitud: status.lastOperarioLongitud,
                  historyPoints: validHistory,
                  lastLocationAt: status.lastLocationAt,
                ),
                const SizedBox(height: 16),
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Ubicacion del operario',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      if (_hasLastLocation(status)) ...[
                        Text(
                          'Ultima ubicacion registrada',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '${status.lastOperarioLatitud!.toStringAsFixed(5)}, ${status.lastOperarioLongitud!.toStringAsFixed(5)}',
                        ),
                        if (status.lastLocationAt != null) ...[
                          const SizedBox(height: 8),
                          Text(
                            'Actualizada: ${_formatDate(status.lastLocationAt)}',
                          ),
                        ],
                        if (status.currentDistanceMeters != null) ...[
                          const SizedBox(height: 8),
                          Text(
                            'Distancia aproximada: ${(status.currentDistanceMeters! / 1000).toStringAsFixed(2)} km',
                          ),
                        ],
                        if (status.etaText != null) ...[
                          const SizedBox(height: 4),
                          Text('ETA: ${status.etaText}'),
                        ],
                      ] else
                        const Text(
                          'Aun no hay ubicacion en tiempo real del operario.',
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                if (recentHistory.isEmpty)
                  const AppEmptyView(
                    message: 'Aun no hay historial de ubicacion.',
                  )
                else
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Historial de ubicacion',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        ...recentHistory.map(
                          (point) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _formatDate(point.fechaHora),
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
                                Text(
                                  '${point.latitud!.toStringAsFixed(5)}, ${point.longitud!.toStringAsFixed(5)}',
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (status.serviceState ==
                        'COMPLETADO_PENDIENTE_CONFIRMACION')
                      OutlinedButton(
                        onPressed: () => context.push(
                          AppRoutes.serviceFinalizationPath(widget.serviceId),
                        ),
                        child: const Text('Validar resolucion'),
                      ),
                    if (status.serviceState == 'FINALIZADO_PENDIENTE_PAGO')
                      OutlinedButton(
                        onPressed: () => context.push(
                          AppRoutes.servicePaymentPath(widget.serviceId),
                        ),
                        child: const Text('Pagar servicio'),
                      ),
                    if (status.serviceState == 'PAGADO')
                      OutlinedButton(
                        onPressed: () => context.push(
                          AppRoutes.serviceRatingPath(widget.serviceId),
                        ),
                        child: const Text('Calificar servicio'),
                      ),
                    OutlinedButton(
                      onPressed: () => context.push(
                        AppRoutes.servicePrequotationPath(widget.serviceId),
                      ),
                      child: const Text('Ver pre-cotizacion'),
                    ),
                    OutlinedButton(
                      onPressed: () => context.go(AppRoutes.clientHome),
                      child: const Text('Volver al inicio'),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

bool _hasLastLocation(dynamic status) {
  return status.lastOperarioLatitud != null &&
      status.lastOperarioLongitud != null;
}

bool _shouldShowLifecycleSummary(String state) {
  return state == 'EN_ESPERA_ASIGNACION' ||
      state == 'COMPLETADO_PENDIENTE_CONFIRMACION' ||
      state == 'FINALIZADO_PENDIENTE_PAGO' ||
      state == 'PAGADO';
}

String _trackingMessage(String serviceState, dynamic status) {
  switch (serviceState) {
    case 'EN_ESPERA_ASIGNACION':
      return 'El taller acepto tu solicitud. Estamos asignando un operario.';
    case 'COMPLETADO_PENDIENTE_CONFIRMACION':
      return 'El servicio fue completado por el taller y esta pendiente de tu validacion.';
    case 'FINALIZADO_PENDIENTE_PAGO':
      return 'La resolucion fue confirmada. El servicio esta pendiente de pago.';
    case 'PAGADO':
      return 'Tu asistencia fue completada y pagada correctamente.';
  }
  if (status.hasLiveLocation == true) {
    return 'Ubicacion del operario disponible.';
  }
  if (status.locationStale == true) {
    return 'La ubicacion del operario puede estar desactualizada.';
  }
  return 'Aun no hay ubicacion en tiempo real del operario.';
}

String _lifecycleSummaryTitle(String state) {
  switch (state) {
    case 'EN_ESPERA_ASIGNACION':
      return 'Asignando operario';
    case 'COMPLETADO_PENDIENTE_CONFIRMACION':
      return 'Validacion pendiente';
    case 'FINALIZADO_PENDIENTE_PAGO':
      return 'Pendiente de pago';
    case 'PAGADO':
      return 'Servicio pagado';
    default:
      return 'Estado del servicio';
  }
}

String _lifecycleSummaryMessage(String state) {
  switch (state) {
    case 'EN_ESPERA_ASIGNACION':
      return 'El taller acepto tu solicitud y estamos asignando un operario para atenderte.';
    case 'COMPLETADO_PENDIENTE_CONFIRMACION':
      return 'El servicio fue completado y ahora debes validar la resolucion.';
    case 'FINALIZADO_PENDIENTE_PAGO':
      return 'La resolucion fue confirmada. Ya puedes registrar el pago del servicio.';
    case 'PAGADO':
      return 'Tu asistencia fue completada y pagada correctamente.';
    default:
      return '';
  }
}

String _mapTrackingError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 404) return 'No se encontro el servicio.';
    if (error.statusCode == 409) {
      return 'El seguimiento en tiempo real aun no esta disponible.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesion expiro. Inicia sesion nuevamente.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo cargar el seguimiento.';
    }
  }
  return 'No se pudo conectar con el servidor.';
}

String _friendlyServiceState(String state) {
  switch (state) {
    case 'EN_ESPERA_ASIGNACION':
      return 'En espera de asignacion';
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
    case 'ESPERANDO_REPUESTOS':
      return 'Esperando repuestos';
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
  if (value == null) return 'Fecha no disponible';
  final localValue = value.toLocal();
  return '${localValue.day.toString().padLeft(2, '0')}/'
      '${localValue.month.toString().padLeft(2, '0')}/'
      '${localValue.year} '
      '${localValue.hour.toString().padLeft(2, '0')}:'
      '${localValue.minute.toString().padLeft(2, '0')}';
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
