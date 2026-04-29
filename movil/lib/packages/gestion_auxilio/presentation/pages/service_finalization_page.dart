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
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/models/client_active_service_model.dart';
import '../../data/models/finalization_status_model.dart';
import '../controllers/active_services_controller.dart';
import '../controllers/service_finalization_controller.dart';

class ServiceFinalizationPage extends ConsumerStatefulWidget {
  const ServiceFinalizationPage({
    super.key,
    required this.serviceId,
  });

  final int serviceId;

  @override
  ConsumerState<ServiceFinalizationPage> createState() =>
      _ServiceFinalizationPageState();
}

class _ServiceFinalizationPageState
    extends ConsumerState<ServiceFinalizationPage> {
  bool _submitting = false;

  @override
  Widget build(BuildContext context) {
    final finalizationState =
        ref.watch(serviceFinalizationProvider(widget.serviceId));
    final activeServices = ref.watch(activeServicesProvider).valueOrNull;
    final serviceSummary = _findServiceSummary(activeServices, widget.serviceId);

    return AppPageScaffold(
      label: 'VALIDACIÓN',
      title: 'Validar resolución',
      subtitle: 'Confirma si el auxilio resolvió tu problema.',
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: _submitting
            ? null
            : () => ref
                .read(serviceFinalizationProvider(widget.serviceId).notifier)
                .refresh(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      child: finalizationState.when(
        loading: () => const AppLoading(message: 'Cargando validación...'),
        error: (error, _) => AppErrorView(
          message: _mapFinalizationError(error),
          onRetry: () => ref
              .read(serviceFinalizationProvider(widget.serviceId).notifier)
              .refresh(),
        ),
        data: (data) => RefreshIndicator(
          onRefresh: () => ref
              .read(serviceFinalizationProvider(widget.serviceId).notifier)
              .refresh(),
          child: ListView(
            children: [
              _StatusCard(
                data: data,
                serviceSummary: serviceSummary,
              ),
              const SizedBox(height: 16),
              _ReportCard(data: data),
              const SizedBox(height: 16),
              _buildDecisionCard(context, data),
              const SizedBox(height: 16),
              if (data.timeline.isEmpty)
                const AppEmptyView(
                  message: 'Aún no hay eventos de validación registrados.',
                )
              else
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Historial de validación',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      ...data.timeline.map(
                        (item) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _friendlyTimelineAction(item.action),
                                style: Theme.of(context).textTheme.titleSmall,
                              ),
                              const SizedBox(height: 4),
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
                              if (item.newState != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  'Estado: ${localizeStatusLabel(item.newState)}',
                                ),
                              ],
                              if (item.motivo != null &&
                                  item.motivo!.trim().isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Text('Motivo: ${item.motivo!}'),
                              ],
                              if (item.durationSeconds != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  'Duración total: ${_formatDuration(item.durationSeconds!)}',
                                ),
                              ],
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
                  OutlinedButton(
                    onPressed: () => context.go(
                      AppRoutes.serviceTrackingPath(widget.serviceId),
                    ),
                    child: const Text('Volver al seguimiento'),
                  ),
                  OutlinedButton(
                    onPressed: () => context.go(AppRoutes.clientHome),
                    child: const Text('Volver al inicio'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDecisionCard(
    BuildContext context,
    FinalizationStatusModel data,
  ) {
    final controller =
        ref.read(serviceFinalizationProvider(widget.serviceId).notifier);

    if (data.serviceState == 'PAGADO') {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Servicio pagado',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text('Este servicio ya fue pagado.'),
            const SizedBox(height: 16),
            AppPrimaryButton(
              label: 'Calificar servicio',
              onPressed: () =>
                  context.push(AppRoutes.serviceRatingPath(widget.serviceId)),
            ),
          ],
        ),
      );
    }

    if (data.serviceState == 'FINALIZADO_PENDIENTE_PAGO' ||
        data.confirmedAt != null) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Resolución confirmada',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Resolución confirmada. El servicio está pendiente de pago.',
            ),
            const SizedBox(height: 16),
            AppPrimaryButton(
              label: 'Pagar servicio',
              onPressed: () =>
                  context.push(AppRoutes.servicePaymentPath(widget.serviceId)),
            ),
          ],
        ),
      );
    }

    if (!data.finalizationEligible) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Validación no disponible',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'El servicio aún no está listo para validación.',
            ),
            const SizedBox(height: 16),
            AppPrimaryButton(
              label: 'Volver al seguimiento',
              onPressed: () =>
                  context.go(AppRoutes.serviceTrackingPath(widget.serviceId)),
            ),
          ],
        ),
      );
    }

    if (!data.clientDecisionPending) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Validación registrada',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Ya no hay una validación pendiente del cliente para este servicio.',
            ),
            const SizedBox(height: 16),
            AppPrimaryButton(
              label: 'Actualizar',
              onPressed: _submitting ? null : controller.refresh,
            ),
          ],
        ),
      );
    }

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Validación pendiente',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          const Text(
            'El taller indica que el servicio fue completado. Confirma si el problema quedó resuelto.',
          ),
          const SizedBox(height: 16),
          AppPrimaryButton(
            label: 'Confirmar resolución',
            isLoading: _submitting,
            onPressed: _submitting ? null : _confirmResolution,
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: _submitting ? null : _rejectResolution,
              child: const Text('Reportar inconformidad'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmResolution() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('¿Confirmar resolución?'),
        content: const Text('Al confirmar, el servicio pasará a pago.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Confirmar'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() => _submitting = true);
    try {
      final response = await ref
          .read(serviceFinalizationProvider(widget.serviceId).notifier)
          .confirm();
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            localizeBackendMessage(response.message).isNotEmpty
                ? localizeBackendMessage(response.message)
                : 'Resolución confirmada. Ahora puedes realizar el pago.',
          ),
        ),
      );
      context.go(AppRoutes.servicePaymentPath(widget.serviceId));
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_mapFinalizationError(error))),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  Future<void> _rejectResolution() async {
    final controller = TextEditingController();
    String? validationError;

    final motivo = await showDialog<String>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Motivo de inconformidad'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                maxLength: 2000,
                minLines: 3,
                maxLines: 5,
                decoration: InputDecoration(
                  labelText: 'Describe el motivo',
                  errorText: validationError,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () {
                final value = controller.text.trim();
                if (value.isEmpty) {
                  setDialogState(() {
                    validationError = 'Debes ingresar el motivo de inconformidad.';
                  });
                  return;
                }
                Navigator.of(dialogContext).pop(value);
              },
              child: const Text('Enviar'),
            ),
          ],
        ),
      ),
    );

    controller.dispose();

    if (motivo == null || motivo.trim().isEmpty || !mounted) {
      return;
    }

    setState(() => _submitting = true);
    try {
      final response = await ref
          .read(serviceFinalizationProvider(widget.serviceId).notifier)
          .reject(motivo);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            localizeBackendMessage(response.message).isNotEmpty
                ? localizeBackendMessage(response.message)
                : 'Se registró tu inconformidad y el servicio volvió a revisión.',
          ),
        ),
      );
      context.go(AppRoutes.serviceTrackingPath(widget.serviceId));
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_mapFinalizationError(error))),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.data,
    required this.serviceSummary,
  });

  final FinalizationStatusModel data;
  final ClientActiveServiceModel? serviceSummary;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _InfoRow(
            label: 'Estado del servicio',
            value: localizeStatusLabel(data.serviceState),
          ),
          _InfoRow(
            label: 'Estado del incidente',
            value: localizeStatusLabel(data.incidentState),
          ),
          if (serviceSummary?.workshopName != null)
            _InfoRow(
              label: 'Taller',
              value: serviceSummary!.workshopName!,
            ),
          if (serviceSummary?.operarioName != null)
            _InfoRow(
              label: 'Operario',
              value: serviceSummary!.operarioName!,
            ),
          if (data.confirmedAt != null)
            _InfoRow(
              label: 'Fecha de finalización',
              value: _formatDate(data.confirmedAt),
            ),
          if (_prequotationText(serviceSummary) != null)
            _InfoRow(
              label: 'Pre-cotización',
              value: _prequotationText(serviceSummary)!,
            ),
        ],
      ),
    );
  }
}

class _ReportCard extends StatelessWidget {
  const _ReportCard({required this.data});

  final FinalizationStatusModel data;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Informe técnico',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          if (!data.reportExists)
            const Text('El informe técnico todavía no está disponible.')
          else ...[
            const Text(
              'El taller registró el cierre técnico del servicio. Revisa el historial y las evidencias finales reportadas.',
            ),
            const SizedBox(height: 12),
            _InfoRow(
              label: 'Reporte final',
              value: 'Registrado',
            ),
            _InfoRow(
              label: 'Evidencias finales',
              value: '${data.finalEvidenceCount}',
            ),
          ],
        ],
      ),
    );
  }
}

ClientActiveServiceModel? _findServiceSummary(
  List<ClientActiveServiceModel>? items,
  int serviceId,
) {
  if (items == null) {
    return null;
  }
  for (final item in items) {
    if (item.serviceId == serviceId) {
      return item;
    }
  }
  return null;
}

String? _prequotationText(ClientActiveServiceModel? serviceSummary) {
  if (serviceSummary == null ||
      serviceSummary.prequotationMin == null ||
      serviceSummary.prequotationMax == null) {
    return null;
  }
  final currency = serviceSummary.prequotationCurrency ?? 'BOB';
  return '$currency '
      '${serviceSummary.prequotationMin!.toStringAsFixed(2)} - '
      '${serviceSummary.prequotationMax!.toStringAsFixed(2)}';
}

String _friendlyTimelineAction(String action) {
  switch (action) {
    case 'SERVICIO_LISTO_PARA_VALIDACION':
      return 'Servicio listo para validación';
    case 'FINALIZACION_SOLICITADA':
      return 'Validación solicitada';
    case 'FINALIZACION_CONFIRMADA_CLIENTE':
      return 'Resolución confirmada por el cliente';
    case 'FINALIZACION_RECHAZADA_CLIENTE':
      return 'Inconformidad reportada por el cliente';
    default:
      return localizeBackendMessage(action);
  }
}

String _mapFinalizationError(Object error) {
  if (error is ApiException) {
    final backendDetail = _extractBackendDetail(error.details);
    final localizedDetail = localizeBackendMessage(backendDetail);
    if (localizedDetail.isNotEmpty && localizedDetail != backendDetail) {
      return localizedDetail;
    }
    if (error.statusCode == 404) {
      return 'No se encontró el servicio.';
    }
    if (error.statusCode == 409) {
      return 'El servicio no está en un estado válido para validación.';
    }
    if (error.statusCode == 422) {
      return 'Revisa los datos enviados.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró o no tienes permiso para esta acción.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo validar la resolución.';
    }
  }
  return 'No se pudo conectar con el servidor.';
}

String? _extractBackendDetail(dynamic details) {
  if (details is String) {
    return details;
  }
  if (details is Map<String, dynamic>) {
    final detail = details['detail'];
    if (detail is String) {
      return detail;
    }
    if (detail is Map<String, dynamic>) {
      return _extractBackendDetail(detail);
    }
    if (detail is List && detail.isNotEmpty) {
      final first = detail.first;
      if (first is String) {
        return first;
      }
      if (first is Map<String, dynamic> && first['msg'] is String) {
        return first['msg'] as String;
      }
    }
  }
  return null;
}

String _formatDuration(int seconds) {
  final duration = Duration(seconds: seconds);
  final hours = duration.inHours;
  final minutes = duration.inMinutes.remainder(60);
  if (hours > 0) {
    return '$hours h $minutes min';
  }
  return '${duration.inMinutes} min';
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
