import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/models/offline_incident_queue_item.dart';
import '../controllers/offline_incident_queue_controller.dart';

class PendingIncidentsPage extends ConsumerStatefulWidget {
  const PendingIncidentsPage({super.key, this.initialMessage});

  final String? initialMessage;

  @override
  ConsumerState<PendingIncidentsPage> createState() =>
      _PendingIncidentsPageState();
}

class _PendingIncidentsPageState extends ConsumerState<PendingIncidentsPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      final message = widget.initialMessage;
      if (message != null && message.trim().isNotEmpty) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(message)));
      }
      await ref
          .read(offlineIncidentQueueControllerProvider.notifier)
          .syncPending();
    });
  }

  Future<void> _syncNow() async {
    await ref
        .read(offlineIncidentQueueControllerProvider.notifier)
        .syncPending();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final queueState = ref.watch(offlineIncidentQueueControllerProvider);
    final items = queueState.valueOrNull ?? const <OfflineIncidentQueueItem>[];
    final pendingCount = items
        .where((item) => item.status != OfflineIncidentSyncStatus.sincronizado)
        .length;

    return AppPageScaffold(
      label: 'AUXILIO VIAL',
      title: 'Emergencias pendientes',
      subtitle:
          'Revisa reportes guardados en el dispositivo y sincronizalos cuando vuelva la conexion.',
      actions: IconButton(
        tooltip: 'Volver',
        icon: const Icon(Icons.arrow_back_rounded),
        onPressed: () => context.go(AppRoutes.clientHome),
      ),
      child: RefreshIndicator(
        onRefresh: _syncNow,
        child: ListView(
          children: [
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Pendientes de sincronizacion',
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    pendingCount == 0
                        ? 'No hay emergencias pendientes o con error para reenviar.'
                        : '$pendingCount emergencia${pendingCount == 1 ? '' : 's'} requiere${pendingCount == 1 ? '' : 'n'} seguimiento.',
                    style: theme.textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  AppPrimaryButton(
                    label: 'Sincronizar ahora',
                    icon: Icons.sync_rounded,
                    isLoading: queueState.isLoading,
                    onPressed: queueState.isLoading ? null : _syncNow,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            if (queueState.hasError)
              AppCard(
                child: Text(
                  'No se pudo cargar la cola offline. Intenta nuevamente.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.error,
                  ),
                ),
              )
            else if (!queueState.isLoading && items.isEmpty)
              const AppCard(
                child: Text(
                  'No hay emergencias guardadas localmente en este dispositivo.',
                ),
              )
            else
              ...items.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _PendingIncidentCard(item: item),
                ),
              ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _PendingIncidentCard extends StatelessWidget {
  const _PendingIncidentCard({required this.item});

  final OfflineIncidentQueueItem item;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final statusColor = switch (item.status) {
      OfflineIncidentSyncStatus.pendienteSync => Colors.orange.shade700,
      OfflineIncidentSyncStatus.sincronizando => theme.colorScheme.primary,
      OfflineIncidentSyncStatus.sincronizado => Colors.green.shade700,
      OfflineIncidentSyncStatus.errorSync => theme.colorScheme.error,
    };
    final description = item.description.trim();

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.specialtyLabel,
                      style: theme.textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatDate(item.createdAtLocal),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  item.status.value,
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: statusColor,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            description.isEmpty ? 'Sin descripcion de texto.' : description,
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Text(
            'Ubicacion: ${item.latitud.toStringAsFixed(4)}, ${item.longitud.toStringAsFixed(4)}',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 4),
          Text(
            'Fotos: ${item.photoPaths.length} · Audio: ${item.audioPath == null || item.audioPath!.isEmpty ? 'No' : 'Si'}',
            style: theme.textTheme.bodySmall,
          ),
          if (item.serverIncidentId != null) ...[
            const SizedBox(height: 4),
            Text(
              'Incidente del servidor: #${item.serverIncidentId}',
              style: theme.textTheme.bodySmall,
            ),
          ],
          if (item.lastError != null && item.lastError!.trim().isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              item.lastError!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: item.status == OfflineIncidentSyncStatus.sincronizado
                    ? theme.colorScheme.onSurfaceVariant
                    : theme.colorScheme.error,
              ),
            ),
          ],
          if (item.serverIncidentId != null) ...[
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: () => context.go(
                  AppRoutes.incidentDiagnosisPath(item.serverIncidentId!),
                ),
                icon: const Icon(Icons.analytics_outlined),
                label: const Text('Abrir incidente'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  static String _formatDate(DateTime value) {
    return '${value.day.toString().padLeft(2, '0')}/'
        '${value.month.toString().padLeft(2, '0')}/'
        '${value.year} '
        '${value.hour.toString().padLeft(2, '0')}:'
        '${value.minute.toString().padLeft(2, '0')}';
  }
}
