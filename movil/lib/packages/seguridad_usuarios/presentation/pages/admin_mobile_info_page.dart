import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';

class AdminMobileInfoPage extends ConsumerWidget {
  const AdminMobileInfoPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppPageScaffold(
      label: 'ADMINISTRACIÓN',
      title: 'Panel administrativo',
      subtitle: 'El panel administrativo se gestiona desde la aplicación web.',
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: AppCard(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(
                  Icons.admin_panel_settings_outlined,
                  size: 48,
                ),
                const SizedBox(height: 16),
                const Text(
                  'El panel administrativo se gestiona desde la aplicación web.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                AppPrimaryButton(
                  label: 'Cerrar sesión',
                  onPressed: () async {
                    await ref.read(authControllerProvider.notifier).logout();
                    if (context.mounted) {
                      context.go(AppRoutes.login);
                    }
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
