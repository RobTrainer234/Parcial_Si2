import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AppPageScaffold(
      label: 'Cuenta',
      title: 'Perfil Cliente',
      subtitle: 'La carga del perfil se implementará con CU01.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Perfil disponible próximamente',
                  style: theme.textTheme.titleLarge,
                ),
                const SizedBox(height: 10),
                Text(
                  'Esta vista mostrará la información personal y opciones de cuenta del conductor.',
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => context.pop(),
                  child: const Text('Volver'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: AppPrimaryButton(
                  label: 'Ir al inicio',
                  onPressed: () => context.go(AppRoutes.clientHome),
                  expand: false,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
