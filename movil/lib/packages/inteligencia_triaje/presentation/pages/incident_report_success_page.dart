import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../../../core/widgets/location_label.dart';
import '../../data/models/incident_report_response_model.dart';

class IncidentReportSuccessPage extends StatelessWidget {
  const IncidentReportSuccessPage({super.key, this.result});

  final IncidentReportResponseModel? result;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (result == null) {
      return AppPageScaffold(
        label: 'AUXILIO VIAL',
        title: 'Reporte enviado',
        subtitle: 'No se encontraron datos del reporte.',
        leading: IconButton(
          tooltip: 'Volver',
          onPressed: () => context.pop(),
          icon: const Icon(Icons.arrow_back_rounded),
        ),
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
              const Text('No hay información de reporte disponible.'),
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
      label: 'AUXILIO VIAL',
      title: 'Reporte enviado',
      subtitle: 'Tu incidente fue registrado correctamente.',
      leading: IconButton(
        tooltip: 'Volver',
        onPressed: () {
          if (Navigator.of(context).canPop()) {
            context.pop();
          } else {
            context.go(AppRoutes.clientHome);
          }
        },
        icon: const Icon(Icons.arrow_back_rounded),
      ),
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
                        'Incidente registrado',
                        style: theme.textTheme.titleLarge,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _InfoRow(label: 'Estado', value: result!.status),
                if (result!.especialidadNombre != null)
                  _InfoRow(
                    label: 'Sospecha inicial',
                    value: result!.especialidadNombre!,
                  ),
                if (result!.fechaHora != null)
                  _InfoRow(
                    label: 'Fecha',
                    value: _formatDate(result!.fechaHora!),
                  ),
                _InfoRow(
                  label: 'Ubicación',
                  valueWidget: LocationLabel(
                    latitud: result!.latitud,
                    longitud: result!.longitud,
                  ),
                ),
                if (result!.evidences.isNotEmpty)
                  _InfoRow(
                    label: 'Evidencias',
                    value: '${result!.evidences.length} archivo(s) adjuntos',
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
                  'Descripción enviada',
                  style: theme.textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  result!.descripcionCliente,
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          AppCard(
            child: Text(
              'Ahora puedes solicitar el análisis automático del incidente.',
              style: theme.textTheme.bodyMedium,
            ),
          ),
          const SizedBox(height: 24),
          AppPrimaryButton(
            label: 'Ver diagnóstico',
            icon: Icons.analytics_outlined,
            onPressed: () =>
                context.go(AppRoutes.incidentDiagnosisPath(result!.incidentId)),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => context.go(AppRoutes.clientHome),
              child: const Text('Volver al inicio'),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  String _formatDate(DateTime value) {
    return '${value.day.toString().padLeft(2, '0')}/'
        '${value.month.toString().padLeft(2, '0')}/'
        '${value.year} '
        '${value.hour.toString().padLeft(2, '0')}:'
        '${value.minute.toString().padLeft(2, '0')}';
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.label,
    this.value,
    this.valueWidget,
  });

  final String label;
  final String? value;
  final Widget? valueWidget;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 6),
          valueWidget ?? Text(
            value ?? '',
            style: theme.textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}
