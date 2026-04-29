import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/utils/user_facing_text.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/models/hire_workshop_response_model.dart';

class WorkshopRequestSentPage extends StatelessWidget {
  const WorkshopRequestSentPage({
    super.key,
    required this.incidentId,
    this.result,
  });

  final int incidentId;
  final HireWorkshopResponseModel? result;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (result == null) {
      return AppPageScaffold(
        label: 'SOLICITUD',
        title: 'Solicitud enviada',
        subtitle: 'No se encontraron datos de la solicitud.',
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.info_outline_rounded,
                size: 48,
                color: theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(height: 16),
              const Text(
                'No hay información de solicitud disponible.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              AppPrimaryButton(
                label: 'Volver al inicio',
                onPressed: () => context.go(AppRoutes.clientHome),
              ),
            ],
          ),
        ),
      );
    }

    return AppPageScaffold(
      label: 'SOLICITUD',
      title: 'Solicitud enviada',
      subtitle: 'El taller recibirá tu solicitud de auxilio.',
      child: ListView(
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.check_circle_outline_rounded,
                      size: 28,
                      color: Colors.green.shade600,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        result!.workshopName,
                        style: theme.textTheme.titleLarge,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _InfoRow(
                  label: 'Estado',
                  value: localizeStatusLabel(result!.requestState),
                ),
                if (result!.message.trim().isNotEmpty)
                  _InfoRow(
                    label: 'Detalle',
                    value: localizeBackendMessage(result!.message),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Tu solicitud fue enviada. Espera la respuesta del taller.',
                  style: theme.textTheme.bodyLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Cuando el taller acepte, el servicio aparecerá en Servicios activos y recibirás una notificación.',
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          AppPrimaryButton(
            label: 'Volver al inicio',
            onPressed: () => context.go(AppRoutes.clientHome),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => context.push(AppRoutes.notifications),
              child: const Text('Ver notificaciones'),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => context.push(AppRoutes.activeServices),
              child: const Text('Ver servicios activos'),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () =>
                  context.push(AppRoutes.workshopRecommendationsPath(incidentId)),
              child: const Text('Ver recomendaciones'),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
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
          Text(value, style: theme.textTheme.bodyMedium),
        ],
      ),
    );
  }
}
