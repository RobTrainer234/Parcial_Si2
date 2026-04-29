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

class ServicePrequotationPage extends ConsumerWidget {
  const ServicePrequotationPage({
    super.key,
    required this.serviceId,
  });

  final int serviceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(servicePrequotationProvider(serviceId));

    return AppPageScaffold(
      label: 'PRE-COTIZACIÓN',
      title: 'Pre-cotización técnica',
      subtitle: 'Consulta el rango estimado antes del cierre del servicio.',
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: () => ref.refresh(servicePrequotationProvider(serviceId)),
        icon: const Icon(Icons.refresh_rounded),
      ),
      child: state.when(
        loading: () => const AppLoading(message: 'Cargando pre-cotización...'),
        error: (error, _) => AppErrorView(
          message: _mapPrequotationError(error),
          onRetry: () => ref.refresh(servicePrequotationProvider(serviceId)),
        ),
        data: (data) {
          final hasValues =
              data.prequotationMin != null && data.prequotationMax != null;
          return ListView(
            children: [
              if (!hasValues)
                const AppEmptyView(
                  message: 'La pre-cotización todavía no está disponible.',
                  subtitle:
                      'Se generará cuando el taller complete la evaluación técnica.',
                )
              else
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (data.catalogServiceName != null)
                        _InfoRow(
                          label: 'Servicio',
                          value: data.catalogServiceName!,
                        ),
                      if (data.prequotationCode != null)
                        _InfoRow(
                          label: 'Código',
                          value: data.prequotationCode!,
                        ),
                      _InfoRow(
                        label: 'Rango estimado',
                        value:
                            '${data.prequotationCurrency ?? 'BOB'} ${data.prequotationMin!.toStringAsFixed(2)} - ${data.prequotationMax!.toStringAsFixed(2)}',
                      ),
                      if (data.incluyeRepuestosBasicos != null)
                        _InfoRow(
                          label: 'Repuestos básicos',
                          value: data.incluyeRepuestosBasicos!
                              ? 'Incluidos'
                              : 'No incluidos',
                        ),
                      const SizedBox(height: 8),
                      Text(localizeBackendMessage(data.message)),
                    ],
                  ),
                ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton(
                    onPressed: () =>
                        context.push(AppRoutes.serviceTrackingPath(serviceId)),
                    child: const Text('Ver seguimiento'),
                  ),
                  OutlinedButton(
                    onPressed: () => context.go(AppRoutes.clientHome),
                    child: const Text('Volver al inicio'),
                  ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}

String _mapPrequotationError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 404) return 'No se encontró el servicio.';
    if (error.statusCode == 409) {
      return 'La pre-cotización todavía no está disponible.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo cargar la pre-cotización.';
    }
  }
  return 'No se pudo conectar con el servidor.';
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
