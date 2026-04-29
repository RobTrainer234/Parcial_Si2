import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/utils/user_facing_text.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_empty_view.dart';
import '../../../../core/widgets/app_error_view.dart';
import '../../../../core/widgets/app_loading.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../controllers/operator_services_controller.dart';
import '../../data/models/operator_assigned_service_model.dart';

class OperatorHomePage extends ConsumerWidget {
  const OperatorHomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(operatorServicesProvider);

    return AppPageScaffold(
      label: 'OPERARIO',
      title: 'Servicios asignados',
      subtitle: 'Atiende las asistencias asignadas por tu taller.',
      actions: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            tooltip: 'Actualizar',
            onPressed: () =>
                ref.read(operatorServicesProvider.notifier).refresh(),
            icon: const Icon(Icons.refresh_rounded),
          ),
          IconButton(
            tooltip: 'Cerrar sesion',
            onPressed: () async {
              await ref.read(authControllerProvider.notifier).logout();
              if (context.mounted) {
                context.go(AppRoutes.login);
              }
            },
            icon: const Icon(Icons.logout_rounded),
          ),
        ],
      ),
      child: state.when(
        loading: () => const AppLoading(message: 'Cargando servicios asignados...'),
        error: (error, _) => AppErrorView(
          message: _mapOperatorHomeError(error),
          onRetry: () => ref.read(operatorServicesProvider.notifier).refresh(),
        ),
        data: (items) {
          final operational = items.where(_isOperationalState).toList();
          final closed = items.where((item) => !_isOperationalState(item)).toList();

          if (items.isEmpty) {
            return const AppEmptyView(
              message: 'No tienes servicios asignados en este momento.',
            );
          }

          return RefreshIndicator(
            onRefresh: () => ref.read(operatorServicesProvider.notifier).refresh(),
            child: ListView(
              children: [
                Text(
                  'Servicios por atender',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                if (operational.isEmpty)
                  const AppEmptyView(
                    message: 'No tienes servicios operativos pendientes en este momento.',
                  )
                else
                  ...operational.map((item) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _OperatorServiceCard(
                          item: item,
                          closed: false,
                        ),
                      )),
                const SizedBox(height: 16),
                Text(
                  'Servicios cerrados',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                if (closed.isEmpty)
                  const AppEmptyView(
                    message: 'No tienes servicios cerrados recientes.',
                  )
                else
                  ...closed.map((item) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _OperatorServiceCard(
                          item: item,
                          closed: true,
                        ),
                      )),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _OperatorServiceCard extends StatelessWidget {
  const _OperatorServiceCard({
    required this.item,
    required this.closed,
  });

  final OperatorAssignedServiceModel item;
  final bool closed;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            closed ? 'Servicio cerrado' : 'Servicio de auxilio',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          _InfoRow(
            label: 'Estado',
            value: _friendlyOperatorState(item.serviceState),
          ),
          if (item.detectedSpecialty != null)
            _InfoRow(
              label: 'Especialidad detectada',
              value: item.detectedSpecialty!,
            ),
          if (item.severity != null)
            _InfoRow(
              label: 'Severidad',
              value: localizeStatusLabel(item.severity),
            ),
          if (item.aiSummary != null && item.aiSummary!.trim().isNotEmpty)
            _InfoRow(
              label: 'Resumen IA',
              value: item.aiSummary!,
            ),
          if (item.prequotationMin != null && item.prequotationMax != null)
            _InfoRow(
              label: 'Pre-cotizacion',
              value:
                  '${item.prequotationCurrency ?? 'BOB'} ${item.prequotationMin!.toStringAsFixed(2)} - ${item.prequotationMax!.toStringAsFixed(2)}',
            ),
          if (closed) ...[
            const SizedBox(height: 8),
            const Text(
              'El servicio ya fue cerrado operativamente.',
            ),
          ],
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () => context.push(
              AppRoutes.operatorServicePath(item.serviceId),
            ),
            child: const Text('Ver servicio'),
          ),
        ],
      ),
    );
  }
}

String _mapOperatorHomeError(Object error) {
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
    if (error.statusCode == 422) {
      return 'Revisa los datos enviados.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo cargar el servicio.';
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

bool _isOperationalState(OperatorAssignedServiceModel item) {
  return {
    'ASIGNADO',
    'EN_CAMINO',
    'EN_SITIO',
    'EN_DIAGNOSTICO_FISICO',
    'EN_REPARACION',
  }.contains(item.serviceState);
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
