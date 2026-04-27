import 'package:flutter/material.dart';

import '../../../../core/widgets/app_loading.dart';
import '../../../../core/widgets/app_page_scaffold.dart';

class SplashPage extends StatelessWidget {
  const SplashPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const AppPageScaffold(
      child: AppLoading(message: 'Preparando la sesión...'),
    );
  }
}
