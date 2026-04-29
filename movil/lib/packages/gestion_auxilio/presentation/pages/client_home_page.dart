import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../../seguridad_usuarios/presentation/controllers/profile_controller.dart';
import '../controllers/notifications_controller.dart';

class ClientHomePage extends ConsumerWidget {
  const ClientHomePage({super.key});

  void _showMessage(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final dangerColor = theme.colorScheme.error;
    final profileState = ref.watch(profileControllerProvider);
    final unreadCountAsync = ref.watch(unreadNotificationsCountProvider);
    final vehicleCount = profileState.valueOrNull?.vehicles.length ?? 0;

    return AppPageScaffold(
      label: 'CENTRO DE CONTROL',
      title: 'Inicio Cliente',
      subtitle: 'Accede rápido a las opciones principales de tu asistencia.',
      actions: Semantics(
        button: true,
        label: 'Perfil',
        child: Tooltip(
          message: 'Perfil',
          child: IconButton(
            onPressed: () => context.push(AppRoutes.profile),
            icon: const Icon(Icons.person_rounded, size: 20),
          ),
        ),
      ),
      child: ListView(
        children: [
          AppCard(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Icon(
                        Icons.emergency_share_rounded,
                        color: theme.colorScheme.primary,
                        size: 26,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '¿Necesitas auxilio?',
                            style: theme.textTheme.titleLarge?.copyWith(
                              color: theme.colorScheme.onSurface,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Reporta una falla y solicita asistencia cuando tu vehículo lo necesite.',
                            style: theme.textTheme.bodyLarge,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                AppPrimaryButton(
                  label: 'Reportar incidente',
                  icon: Icons.add_alert_rounded,
                  onPressed: () {
                    if (profileState.isLoading) {
                      _showMessage(
                        context,
                        'Estamos cargando tus vehículos. Intenta nuevamente en unos segundos.',
                      );
                    } else if (profileState.hasError) {
                      _showMessage(
                        context,
                        'No se pudo verificar tus vehículos. Reintenta desde tu perfil.',
                      );
                    } else if (vehicleCount == 0) {
                      _showMessage(
                        context,
                        'Primero registra un vehículo en tu perfil.',
                      );
                    } else {
                      context.push(AppRoutes.reportIncident);
                    }
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          profileState.when(
            loading: () => AppCard(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 22,
                    backgroundColor:
                        theme.colorScheme.primary.withValues(alpha: 0.12),
                    foregroundColor: theme.colorScheme.primary,
                    child: const Icon(Icons.directions_car_rounded, size: 22),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Text(
                      'Cargando tus vehículos...',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                  const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ],
              ),
            ),
            error: (_, __) => AppCard(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 22,
                    backgroundColor:
                        theme.colorScheme.error.withValues(alpha: 0.12),
                    foregroundColor: theme.colorScheme.error,
                    child: const Icon(Icons.error_outline_rounded, size: 22),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Text(
                      'No se pudo cargar tu perfil.',
                      style: theme.textTheme.bodyMedium,
                    ),
                  ),
                  TextButton(
                    onPressed: () =>
                        ref.read(profileControllerProvider.notifier).refresh(),
                    child: const Text('Reintentar'),
                  ),
                ],
              ),
            ),
            data: (profile) {
              final count = profile.vehicles.length;
              return AppCard(
                onTap: () => context.push(AppRoutes.profile),
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 22,
                      backgroundColor:
                          theme.colorScheme.primary.withValues(alpha: 0.12),
                      foregroundColor: theme.colorScheme.primary,
                      child: const Icon(Icons.directions_car_rounded, size: 22),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Vehículos registrados',
                            style: theme.textTheme.titleMedium,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            count == 0
                                ? 'Agrega un vehículo antes de reportar un incidente.'
                                : '$count vehículo${count == 1 ? '' : 's'}',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color:
                                  count == 0 ? theme.colorScheme.error : null,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      'Gestionar',
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: theme.colorScheme.primary,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      Icons.chevron_right_rounded,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: 24),
          Text(
            'Opciones',
            style: theme.textTheme.titleMedium?.copyWith(
              color: theme.colorScheme.onSurface,
            ),
          ),
          const SizedBox(height: 12),
          _HomeActionCard(
            title: 'Servicios activos',
            subtitle: 'Consulta el estado de tus asistencias en curso.',
            icon: Icons.miscellaneous_services_rounded,
            onTap: () => context.push(AppRoutes.activeServices),
          ),
          const SizedBox(height: 12),
          _HomeActionCard(
            title: 'Notificaciones',
            subtitle: 'Revisa avisos sobre solicitudes y servicios.',
            icon: Icons.notifications_none_rounded,
            trailingText: unreadCountAsync.maybeWhen(
              data: (value) => value > 0 ? '$value' : null,
              orElse: () => null,
            ),
            onTap: () => context.push(AppRoutes.notifications),
          ),
          const SizedBox(height: 12),
          Consumer(
            builder: (context, ref, child) {
              final authController = ref.watch(authControllerProvider.notifier);
              return _HomeActionCard(
                title: 'Cerrar sesión',
                subtitle: 'Salir de tu cuenta en este dispositivo.',
                icon: Icons.logout_rounded,
                accentColor: dangerColor,
                onTap: () async {
                  await authController.logout();
                  if (context.mounted) {
                    context.go(AppRoutes.login);
                  }
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

class _HomeActionCard extends StatelessWidget {
  const _HomeActionCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
    this.trailingText,
    this.accentColor,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;
  final String? trailingText;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = accentColor ?? theme.colorScheme.primary;

    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 22,
            backgroundColor: color.withValues(alpha: 0.12),
            foregroundColor: color,
            child: Icon(icon, size: 22),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: accentColor ?? theme.colorScheme.onSurface,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          if (trailingText != null) ...[
            Chip(
              label: Text(trailingText!),
              visualDensity: VisualDensity.compact,
            ),
            const SizedBox(width: 6),
          ],
          Icon(
            Icons.chevron_right_rounded,
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ],
      ),
    );
  }
}
