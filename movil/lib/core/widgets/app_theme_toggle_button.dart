import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../theme/theme_mode_controller.dart';

class AppThemeToggleButton extends ConsumerWidget {
  const AppThemeToggleButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final platformBrightness = MediaQuery.platformBrightnessOf(context);
    final themeMode = ref.watch(themeModeControllerProvider);
    final isDarkActive =
        themeMode == ThemeMode.dark ||
        (themeMode == ThemeMode.system &&
            platformBrightness == Brightness.dark);

    return IconButton(
      tooltip: isDarkActive ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro',
      onPressed: () => ref
          .read(themeModeControllerProvider.notifier)
          .toggle(platformBrightness),
      icon: Icon(
        isDarkActive ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
      ),
    );
  }
}
