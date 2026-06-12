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
import '../controllers/active_services_controller.dart';

class ActiveServicesPage extends ConsumerWidget {
  const ActiveServicesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(activeServicesProvider);

    return AppPageScaffold(
      label: 'SERVICIOS',
      title: 'Servicios activos',
      subtitle: 'Consulta el estado de tus asistencias en curso.',
      leading: IconButton(
        tooltip: 'Volver',
        onPressed: () => context.pop(),
        icon: const Icon(Icons.arrow_back_rounded),
      ),
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: () => ref.read(activeServicesProvider.notifier).refresh(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      child: state.when(
        loading: () => const AppLoading(message: 'Cargando servicios...'),
        error: (error, _) => AppErrorView(
          message: _mapActiveServicesError(error),
          onRetry: () => ref.read(activeServicesProvider.notifier).refresh(),
        ),
        data: (items) {
          if (items.isEmpty) {
            return const Center(
              child: AppEmptyView(
                message: 'No tienes servicios activos por ahora.',
                subtitle:
                    'Cuando un taller acepte tu solicitud, tu asistencia aparecera aqui.',
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () => ref.read(activeServicesProvider.notifier).refresh(),
            child: ListView(
              children: items.map((item) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.workshopName ?? 'Servicio de auxilio',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        _InfoRow(
                          label: 'Estado',
                          value: _friendlyServiceState(item.serviceState),
                        ),
                        if (item.detectedSpecialty != null)
                          _InfoRow(
                            label: 'Especialidad',
                            value: item.detectedSpecialty!,
                          ),
                        if (item.operarioName != null)
                          _InfoRow(
                            label: 'Operario',
                            value: item.operarioName!,
                          ),
                        if (item.prequotationMin != null &&
                            item.prequotationMax != null)
                          _InfoRow(
                            label: 'Pre-cotizacion',
                            value:
                                '${item.prequotationCurrency ?? 'BOB'} ${item.prequotationMin!.toStringAsFixed(2)} - ${item.prequotationMax!.toStringAsFixed(2)}',
                          ),
                        const SizedBox(height: 8),
                        Text(
                          _serviceMessage(item.serviceState),
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            OutlinedButton(
                              onPressed: () => context.push(
                                AppRoutes.serviceTrackingPath(item.serviceId),
                              ),
                              child: const Text('Ver seguimiento'),
                            ),
                            if (item.prequotationMin != null ||
                                item.prequotationMax != null)
                              OutlinedButton(
                                onPressed: () => context.push(
                                  AppRoutes.servicePrequotationPath(item.serviceId),
                                ),
                                child: const Text('Ver pre-cotizacion'),
                              ),
                            if (item.serviceState ==
                                'COMPLETADO_PENDIENTE_CONFIRMACION')
                              OutlinedButton(
                                onPressed: () => context.push(
                                  AppRoutes.serviceFinalizationPath(
                                    item.serviceId,
                                  ),
                                ),
                                child: const Text('Validar resolucion'),
                              ),
                            if (item.serviceState ==
                                'FINALIZADO_PENDIENTE_PAGO')
                              OutlinedButton(
                                onPressed: () => context.push(
                                  AppRoutes.servicePaymentPath(item.serviceId),
                                ),
                                child: const Text('Pagar servicio'),
                              ),
                            if (item.serviceState == 'PAGADO')
                              OutlinedButton(
                                onPressed: () => context.push(
                                  AppRoutes.serviceRatingPath(item.serviceId),
                                ),
                                child: const Text('Calificar servicio'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
          );
        },
      ),
    );
  }
}

String _mapActiveServicesError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 404) {
      return 'No se encontraron servicios activos.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudieron cargar tus servicios.';
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
      return 'Operario en camino';
    case 'EN_SITIO':
      return 'Operario en el lugar';
    case 'EN_DIAGNOSTICO_FISICO':
      return 'Diagnostico en curso';
    case 'EN_REPARACION':
      return 'Reparacion en curso';
    case 'ESPERANDO_REPUESTOS':
      return 'Esperando repuestos';
    case 'COMPLETADO_PENDIENTE_CONFIRMACION':
      return 'Pendiente de confirmacion';
    case 'FINALIZADO_PENDIENTE_PAGO':
      return 'Pendiente de pago';
    case 'PAGADO':
      return 'Pagado';
    default:
      return localizeStatusLabel(state);
  }
}

String _serviceMessage(String state) {
  switch (state) {
    case 'EN_ESPERA_ASIGNACION':
      return 'El taller acepto tu solicitud. Estamos asignando un operario.';
    case 'COMPLETADO_PENDIENTE_CONFIRMACION':
      return 'Tu asistencia fue atendida. Ahora debes validar la resolucion.';
    case 'FINALIZADO_PENDIENTE_PAGO':
      return 'La resolucion fue confirmada. Ya puedes realizar el pago.';
    case 'PAGADO':
      return 'Tu asistencia fue completada y pagada. Ya puedes calificar la atencion.';
    default:
      return 'Tu asistencia sigue en curso.';
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
