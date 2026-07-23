import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../packages/gestion_auxilio/data/models/hire_workshop_response_model.dart';
import '../../packages/gestion_auxilio/presentation/pages/active_services_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/client_home_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/client_service_history_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/maintenance_appointments_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/notifications_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/service_finalization_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/service_prequotation_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/service_tracking_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/workshop_recommendations_page.dart';
import '../../packages/gestion_auxilio/presentation/pages/workshop_request_sent_page.dart';
import '../../packages/finanzas_seguros/presentation/pages/service_payment_page.dart';
import '../../packages/inteligencia_triaje/data/models/incident_report_response_model.dart';
import '../../packages/inteligencia_triaje/presentation/pages/incident_diagnosis_page.dart';
import '../../packages/inteligencia_triaje/presentation/pages/incident_matchmaking_page.dart';
import '../../packages/inteligencia_triaje/presentation/pages/pending_incidents_page.dart';
import '../../packages/inteligencia_triaje/presentation/pages/incident_report_page.dart';
import '../../packages/inteligencia_triaje/presentation/pages/incident_report_success_page.dart';
import '../../packages/operaciones_taller/presentation/pages/operator_home_page.dart';
import '../../packages/operaciones_taller/presentation/pages/operator_service_detail_page.dart';
import '../../packages/reputacion_auditoria/presentation/pages/service_rating_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/admin_mobile_info_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/client_register_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/forgot_password_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/login_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/profile_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/reset_password_page.dart';
import '../../packages/seguridad_usuarios/presentation/pages/splash_page.dart';
import '../auth/auth_controller.dart';
import 'app_routes.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>();

int? _parsePositiveParam(GoRouterState state, String key) {
  final raw = state.pathParameters[key];
  final parsed = raw == null ? null : int.tryParse(raw);
  if (parsed == null || parsed <= 0) {
    return null;
  }
  return parsed;
}

Widget _invalidEntityPage(
  BuildContext context,
  String label, {
  required String homeRoute,
}) {
  return Scaffold(
    body: Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline_rounded, size: 48),
          const SizedBox(height: 16),
          Text('$label no valido.'),
          const SizedBox(height: 16),
          OutlinedButton(
            onPressed: () => context.go(homeRoute),
            child: const Text('Volver al inicio'),
          ),
        ],
      ),
    ),
  );
}

final appRouterProvider = Provider<GoRouter>((ref) {
  final routerRefresh = ValueNotifier<int>(0);
  ref.onDispose(routerRefresh.dispose);
  ref.listen<AsyncValue<dynamic>>(authControllerProvider, (_, __) {
    routerRefresh.value++;
  });

  bool isProtectedRoute(String location) {
    return location.startsWith('/cliente/') ||
        location.startsWith('/operario/') ||
        location.startsWith('/admin/') ||
        location.startsWith('/profile') ||
        location.startsWith('/incident/') ||
        location.startsWith('/notifications') ||
        location.startsWith('/services/');
  }

  bool isClientOnlyRoute(String location) {
    return location.startsWith('/cliente/') ||
        location.startsWith('/incident/') ||
        location.startsWith('/services/');
  }

  bool isOperatorOnlyRoute(String location) {
    return location.startsWith('/operario/');
  }

  bool isAdminOnlyRoute(String location) {
    return location.startsWith('/admin/');
  }

  bool isPublicOnlyRoute(String location) {
    return location == AppRoutes.login ||
        location == AppRoutes.forgotPassword ||
        location == AppRoutes.resetPassword ||
        location == AppRoutes.registerClient ||
        location == AppRoutes.registerClientVerify ||
        location == AppRoutes.splash;
  }

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: AppRoutes.splash,
    refreshListenable: routerRefresh,
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashPage(),
      ),
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>?;
          return LoginPage(
            initialEmail: extra?['initial_email'] as String?,
            successMessage: extra?['success_message'] as String?,
          );
        },
      ),
      GoRoute(
        path: AppRoutes.forgotPassword,
        builder: (context, state) => const ForgotPasswordPage(),
      ),
      GoRoute(
        path: AppRoutes.resetPassword,
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>?;
          return ResetPasswordPage(
            initialToken: extra?['initial_token'] as String?,
          );
        },
      ),
      GoRoute(
        path: AppRoutes.registerClient,
        builder: (context, state) => const ClientRegisterPage(),
      ),
      GoRoute(
        path: AppRoutes.registerClientVerify,
        builder: (context, state) => const ClientRegisterPage(),
      ),
      GoRoute(
        path: AppRoutes.clientHome,
        builder: (context, state) => const ClientHomePage(),
      ),
      GoRoute(
        path: AppRoutes.operatorHome,
        builder: (context, state) => const OperatorHomePage(),
      ),
      GoRoute(
        path: AppRoutes.adminMobileInfo,
        builder: (context, state) => const AdminMobileInfoPage(),
      ),
      GoRoute(
        path: AppRoutes.profile,
        builder: (context, state) => const ProfilePage(),
      ),
      GoRoute(
        path: AppRoutes.notifications,
        builder: (context, state) => const NotificationsPage(),
      ),
      GoRoute(
        path: AppRoutes.activeServices,
        builder: (context, state) => const ActiveServicesPage(),
      ),
      GoRoute(
        path: AppRoutes.serviceHistory,
        builder: (context, state) => const ClientServiceHistoryPage(),
      ),
      GoRoute(
        path: AppRoutes.maintenanceAppointments,
        builder: (context, state) => const MaintenanceAppointmentsPage(),
      ),
      GoRoute(
        path: AppRoutes.reportIncident,
        builder: (context, state) => const IncidentReportPage(),
      ),
      GoRoute(
        path: AppRoutes.pendingIncidents,
        builder: (context, state) =>
            PendingIncidentsPage(initialMessage: state.extra as String?),
      ),
      GoRoute(
        path: AppRoutes.incidentReported,
        builder: (context, state) {
          final result = state.extra as IncidentReportResponseModel?;
          return IncidentReportSuccessPage(result: result);
        },
      ),
      GoRoute(
        path: '/incident/:incidentId/diagnosis',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'incidentId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Incidente',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return IncidentDiagnosisPage(incidentId: id);
        },
      ),
      GoRoute(
        path: '/incident/:incidentId/matchmaking',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'incidentId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Incidente',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return IncidentMatchmakingPage(incidentId: id);
        },
      ),
      GoRoute(
        path: '/incident/:incidentId/recommendations',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'incidentId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Incidente',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return WorkshopRecommendationsPage(incidentId: id);
        },
      ),
      GoRoute(
        path: '/incident/:incidentId/request-sent',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'incidentId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Incidente',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          final result = state.extra as HireWorkshopResponseModel?;
          return WorkshopRequestSentPage(incidentId: id, result: result);
        },
      ),
      GoRoute(
        path: '/services/:serviceId/tracking',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'serviceId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Servicio',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return ServiceTrackingPage(serviceId: id);
        },
      ),
      GoRoute(
        path: '/services/:serviceId/prequotation',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'serviceId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Servicio',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return ServicePrequotationPage(serviceId: id);
        },
      ),
      GoRoute(
        path: '/services/:serviceId/finalization',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'serviceId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Servicio',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return ServiceFinalizationPage(serviceId: id);
        },
      ),
      GoRoute(
        path: '/services/:serviceId/payment',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'serviceId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Servicio',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return ServicePaymentPage(serviceId: id);
        },
      ),
      GoRoute(
        path: '/services/:serviceId/rating',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'serviceId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Servicio',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return ServiceRatingPage(serviceId: id);
        },
      ),
      GoRoute(
        path: '/operario/services/:serviceId',
        builder: (context, state) {
          final role = ref.read(authControllerProvider).valueOrNull?.role;
          final id = _parsePositiveParam(state, 'serviceId');
          if (id == null) {
            return _invalidEntityPage(
              context,
              'Servicio',
              homeRoute: AppRoutes.homeForRole(role),
            );
          }
          return OperatorServiceDetailPage(serviceId: id);
        },
      ),
    ],
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      final role = authState.valueOrNull?.role;
      final homeRoute = AppRoutes.homeForRole(role);
      final location = state.matchedLocation;
      final isLoading = authState.isLoading;
      final isAuthenticated = authState.valueOrNull?.isAuthenticated == true;

      debugPrint(
        'AppRouter.redirect: location=$location loading=$isLoading authenticated=$isAuthenticated role=$role',
      );

      if (isLoading) {
        return location == AppRoutes.splash ? null : AppRoutes.splash;
      }

      if (!isAuthenticated && isProtectedRoute(location)) {
        return AppRoutes.login;
      }

      if (!isAuthenticated && location == AppRoutes.splash) {
        return AppRoutes.login;
      }

      if (isAuthenticated && isPublicOnlyRoute(location)) {
        return homeRoute;
      }

      if (AppRoutes.isOperatorRole(role) && isClientOnlyRoute(location)) {
        return AppRoutes.operatorHome;
      }

      if (AppRoutes.isClientRole(role) && isOperatorOnlyRoute(location)) {
        return AppRoutes.clientHome;
      }

      if (AppRoutes.isAdminRole(role) &&
          (isClientOnlyRoute(location) || isOperatorOnlyRoute(location))) {
        return AppRoutes.adminMobileInfo;
      }

      if (!AppRoutes.isAdminRole(role) && isAdminOnlyRoute(location)) {
        return homeRoute;
      }

      return null;
    },
  );
});
