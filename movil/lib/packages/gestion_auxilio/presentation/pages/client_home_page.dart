import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';

class ClientHomePage extends StatelessWidget {
  const ClientHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AppPageScaffold(
      label: 'Centro de control',
      title: 'Inicio Cliente',
      subtitle: 'Aquí se mostrarán las acciones principales del conductor.',
      child: ListView(
        children: [
          _HomeCard(
            title: 'Reportar incidente',
            subtitle: 'Accede rápidamente al flujo principal de asistencia.',
            icon: Icons.report_gmailerrorred_rounded,
            onTap: null,
          ),
          const SizedBox(height: 14),
          _HomeCard(
            title: 'Servicios activos',
            subtitle: 'Aquí verás el seguimiento de la asistencia en curso.',
            icon: Icons.miscellaneous_services_rounded,
            onTap: null,
          ),
          const SizedBox(height: 14),
          _HomeCard(
            title: 'Notificaciones',
            subtitle: 'Tus avisos importantes aparecerán en esta sección.',
            icon: Icons.notifications_none_rounded,
            onTap: null,
          ),
          const SizedBox(height: 14),
          AppCard(
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                backgroundColor: theme.colorScheme.primary.withValues(alpha: 0.12),
                foregroundColor: theme.colorScheme.primary,
                child: const Icon(Icons.person_outline_rounded),
              ),
              title: Text('Perfil', style: theme.textTheme.titleMedium),
              subtitle: Text(
                'Consulta la información general de tu cuenta.',
                style: theme.textTheme.bodyMedium,
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => context.push(AppRoutes.profile),
            ),
          ),
        ],
      ),
    );
  }
}

class _HomeCard extends StatelessWidget {
  const _HomeCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AppCard(
      child: ListTile(
        contentPadding: EdgeInsets.zero,
        leading: CircleAvatar(
          radius: 24,
          backgroundColor: theme.colorScheme.primary.withValues(alpha: 0.12),
          foregroundColor: theme.colorScheme.primary,
          child: Icon(icon),
        ),
        title: Text(title, style: theme.textTheme.titleMedium),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(subtitle, style: theme.textTheme.bodyMedium),
        ),
        trailing: onTap != null ? const Icon(Icons.chevron_right_rounded) : null,
        onTap: onTap,
      ),
    );
  }
}
