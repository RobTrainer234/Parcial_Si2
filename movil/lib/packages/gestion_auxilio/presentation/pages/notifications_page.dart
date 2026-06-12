import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/realtime/realtime_service.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/utils/user_facing_text.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_empty_view.dart';
import '../../../../core/widgets/app_error_view.dart';
import '../../../../core/widgets/app_loading.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../controllers/notifications_controller.dart';

class NotificationsPage extends ConsumerWidget {
  const NotificationsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(notificationsControllerProvider);
    final realtimeStatus =
        ref.watch(realtimeConnectionStatusProvider).valueOrNull;

    return AppPageScaffold(
      label: 'AVISOS',
      title: 'Notificaciones',
      subtitle: realtimeStatus == RealtimeConnectionStatus.connected
          ? 'WebSocket conectado: las novedades aparecen en tiempo real.'
          : 'Push permanece activo; conectando el canal WebSocket en vivo.',
      leading: IconButton(
        tooltip: 'Volver',
        onPressed: () => context.pop(),
        icon: const Icon(Icons.arrow_back_rounded),
      ),
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: () =>
            ref.read(notificationsControllerProvider.notifier).refresh(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      child: state.when(
        loading: () => const AppLoading(message: 'Cargando notificaciones...'),
        error: (error, _) => AppErrorView(
          message: _mapNotificationsError(error),
          onRetry: () =>
              ref.read(notificationsControllerProvider.notifier).refresh(),
        ),
        data: (data) {
          if (data.items.isEmpty) {
            return AppEmptyView(
              message: 'No tienes notificaciones por ahora.',
              subtitle: data.onlyUnread
                  ? 'No hay avisos sin leer en este momento.'
                  : null,
            );
          }

          return RefreshIndicator(
            onRefresh: () =>
                ref.read(notificationsControllerProvider.notifier).refresh(),
            child: ListView(
              children: [
                AppCard(
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          'No leídas: ${data.unreadCount}',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                      ChoiceChip(
                        label: const Text('Todas'),
                        selected: !data.onlyUnread,
                        onSelected: (_) => ref
                            .read(notificationsControllerProvider.notifier)
                            .setOnlyUnread(false),
                      ),
                      const SizedBox(width: 8),
                      ChoiceChip(
                        label: const Text('No leídas'),
                        selected: data.onlyUnread,
                        onSelected: (_) => ref
                            .read(notificationsControllerProvider.notifier)
                            .setOnlyUnread(true),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                ...data.items.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Text(
                                  item.title,
                                  style: Theme.of(context).textTheme.titleMedium,
                                ),
                              ),
                              if (item.isUnread)
                                const Chip(
                                  label: Text('Nueva'),
                                  visualDensity: VisualDensity.compact,
                                ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(localizeBackendMessage(item.message)),
                          const SizedBox(height: 10),
                          Text(
                            _formatDate(item.createdAt),
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(
                                  color: Theme.of(context)
                                      .colorScheme
                                      .onSurfaceVariant,
                                ),
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              if (item.routeSuggested != null &&
                                  item.routeSuggested!.isNotEmpty)
                                OutlinedButton(
                                  onPressed: () => context.push(
                                    item.routeSuggested!,
                                  ),
                                  child: const Text('Abrir'),
                                )
                              else if (item.resolvedServiceId != null)
                                OutlinedButton(
                                  onPressed: () => context.push(
                                    AppRoutes.serviceTrackingPath(
                                      item.resolvedServiceId!,
                                    ),
                                  ),
                                  child: const Text('Ver servicio'),
                                ),
                              if (item.resolvedServiceId == null &&
                                  item.requestId != null)
                                const Chip(
                                  label: Text('Solicitud en proceso'),
                                ),
                              if (item.isUnread)
                                TextButton(
                                  onPressed: () => ref
                                      .read(notificationsControllerProvider
                                          .notifier)
                                      .markAsRead(item.notificationId),
                                  child: const Text('Marcar como leída'),
                                ),
                            ],
                          ),
                        ],
                      ),
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

String _mapNotificationsError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró. Inicia sesión nuevamente.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudieron cargar las notificaciones.';
    }
  }
  return 'No se pudo conectar con el servidor.';
}

String _formatDate(DateTime? value) {
  if (value == null) return 'Fecha no disponible';
  return '${value.day.toString().padLeft(2, '0')}/'
      '${value.month.toString().padLeft(2, '0')}/'
      '${value.year} '
      '${value.hour.toString().padLeft(2, '0')}:'
      '${value.minute.toString().padLeft(2, '0')}';
}
