import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../packages/gestion_auxilio/presentation/pages/client_home_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/login_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/profile_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/splash_page.dart';
import '../auth/auth_controller.dart';
import 'app_routes.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>();

final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authControllerProvider);

  bool isProtectedRoute(String location) {
    return location == AppRoutes.clientHome || location == AppRoutes.profile;
  }

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: AppRoutes.splash,
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashPage(),
      ),
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: AppRoutes.clientHome,
        builder: (context, state) => const ClientHomePage(),
      ),
      GoRoute(
        path: AppRoutes.profile,
        builder: (context, state) => const ProfilePage(),
      ),
    ],
    redirect: (context, state) {
      final location = state.matchedLocation;
      final isLoading = authState.isLoading;
      final isAuthenticated = authState.valueOrNull?.isAuthenticated == true;

      if (isLoading) {
        return location == AppRoutes.splash ? null : AppRoutes.splash;
      }

      if (!isAuthenticated && isProtectedRoute(location)) {
        return AppRoutes.login;
      }

      if (!isAuthenticated && location == AppRoutes.splash) {
        return AppRoutes.login;
      }

      if (isAuthenticated &&
          (location == AppRoutes.splash || location == AppRoutes.login)) {
        return AppRoutes.clientHome;
      }

      return null;
    },
  );
});
