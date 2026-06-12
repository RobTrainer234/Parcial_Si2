import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../../../core/widgets/app_theme_toggle_button.dart';
import '../../../../core/widgets/app_user_mini_profile.dart';
import '../../../inteligencia_triaje/presentation/controllers/offline_incident_queue_controller.dart';
import '../../../seguridad_usuarios/data/models/profile_me_model.dart';
import '../../../seguridad_usuarios/presentation/controllers/profile_controller.dart';
import '../controllers/notifications_controller.dart';

class ClientHomePage extends ConsumerStatefulWidget {
  const ClientHomePage({super.key});

  @override
  ConsumerState<ClientHomePage> createState() => _ClientHomePageState();
}

class _ClientHomePageState extends ConsumerState<ClientHomePage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(offlineIncidentQueueControllerProvider.notifier)
          .syncPending(silent: true);
    });
  }

  void _showMessage(BuildContext context, String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dangerColor = theme.colorScheme.error;
    final profileState = ref.watch(profileControllerProvider);
    final unreadCountAsync = ref.watch(unreadNotificationsCountProvider);
    final offlinePendingCount = ref.watch(offlinePendingIncidentCountProvider);
    final session = ref.watch(authControllerProvider).valueOrNull;
    final vehicleCount = profileState.valueOrNull?.vehicles.length ?? 0;

    return AppPageScaffold(
      label: 'CENTRO DE CONTROL',
      title: 'Inicio cliente',
      subtitle: 'Accede rapido a las opciones principales de tu asistencia.',
      actions: _ClientHeaderActions(
        profile: profileState.valueOrNull,
        fallbackEmail: session?.user?.email,
        unreadCount: unreadCountAsync.valueOrNull,
        onOpenProfile: () => context.push(AppRoutes.profile),
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
                        color: theme.colorScheme.primary.withValues(
                          alpha: 0.12,
                        ),
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
                            'Necesitas auxilio?',
                            style: theme.textTheme.titleLarge?.copyWith(
                              color: theme.colorScheme.onSurface,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Reporta una falla y solicita asistencia cuando tu vehiculo lo necesite.',
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
                        'Estamos cargando tus vehiculos. Intenta nuevamente en unos segundos.',
                      );
                    } else if (profileState.hasError) {
                      _showMessage(
                        context,
                        'No se pudo verificar tus vehiculos. Reintenta desde tu perfil.',
                      );
                    } else if (vehicleCount == 0) {
                      _showMessage(
                        context,
                        'Primero registra un vehiculo en tu perfil.',
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
                    backgroundColor: theme.colorScheme.primary.withValues(
                      alpha: 0.12,
                    ),
                    foregroundColor: theme.colorScheme.primary,
                    child: const Icon(Icons.directions_car_rounded, size: 22),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Text(
                      'Cargando tus vehiculos...',
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
                    backgroundColor: theme.colorScheme.error.withValues(
                      alpha: 0.12,
                    ),
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
                padding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 16,
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 22,
                      backgroundColor: theme.colorScheme.primary.withValues(
                        alpha: 0.12,
                      ),
                      foregroundColor: theme.colorScheme.primary,
                      child: const Icon(Icons.directions_car_rounded, size: 22),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Vehiculos registrados',
                            style: theme.textTheme.titleMedium,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            count == 0
                                ? 'Agrega un vehiculo antes de reportar un incidente.'
                                : '$count vehiculo${count == 1 ? '' : 's'}',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: count == 0
                                  ? theme.colorScheme.error
                                  : null,
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
          _HomeActionCard(
            title: 'Emergencias pendientes',
            subtitle:
                'Consulta reportes guardados sin conexion y fuerza su sincronizacion.',
            icon: Icons.cloud_sync_outlined,
            trailingText: offlinePendingCount > 0
                ? '$offlinePendingCount'
                : null,
            onTap: () => context.push(AppRoutes.pendingIncidents),
          ),
          const SizedBox(height: 12),
          _HomeActionCard(
            title: 'Cerrar sesion',
            subtitle: 'Salir de tu cuenta en este dispositivo.',
            icon: Icons.logout_rounded,
            accentColor: dangerColor,
            onTap: () async {
              await ref.read(authControllerProvider.notifier).logout();
              if (context.mounted) {
                context.go(AppRoutes.login);
              }
            },
          ),
        ],
      ),
    );
  }
}

class _ClientHeaderActions extends StatelessWidget {
  const _ClientHeaderActions({
    required this.profile,
    required this.fallbackEmail,
    required this.unreadCount,
    required this.onOpenProfile,
  });

  final ProfileMeModel? profile;
  final String? fallbackEmail;
  final int? unreadCount;
  final VoidCallback onOpenProfile;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 184,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          AppUserMiniProfile(
            title: _clientName(profile, fallbackEmail),
            subtitle: _clientSubtitle(profile),
            badgeCount: unreadCount,
            icon: Icons.person_pin_circle_rounded,
            onTap: onOpenProfile,
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const AppThemeToggleButton(),
              IconButton(
                tooltip: 'Perfil',
                onPressed: onOpenProfile,
                icon: const Icon(Icons.person_rounded, size: 20),
              ),
            ],
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
                Text(subtitle, style: theme.textTheme.bodyMedium),
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

String _clientName(ProfileMeModel? profile, String? fallbackEmail) {
  if (profile != null) {
    return '${profile.persona.nombre} ${profile.persona.apellido}'.trim();
  }
  if (fallbackEmail != null && fallbackEmail.trim().isNotEmpty) {
    return fallbackEmail.trim();
  }
  return 'Conductor';
}

String _clientSubtitle(ProfileMeModel? profile) {
  if (profile == null || profile.vehicles.isEmpty) {
    return 'Conductor';
  }
  final vehicle = profile.vehicles.first;
  return '${vehicle.marcaNombre} ${vehicle.modeloNombre}';
}
