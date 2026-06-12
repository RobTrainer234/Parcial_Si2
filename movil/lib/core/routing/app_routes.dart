class AppRoutes {
  static const splash = '/splash';
  static const login = '/login';
  static const forgotPassword = '/forgot-password';
  static const resetPassword = '/reset-password';
  static const registerClient = '/register/client';
  static const registerClientVerify = '/register/client/verify';
  static const clientHome = '/cliente/home';
  static const operatorHome = '/operario/home';
  static const adminMobileInfo = '/admin/mobile-info';
  static const profile = '/profile';
  static const notifications = '/notifications';
  static const activeServices = '/services/active';
  static const reportIncident = '/incident/report';
  static const incidentReported = '/incident/reported';

  // Phase C: parameterized routes
  static String incidentDiagnosisPath(int incidentId) =>
      '/incident/$incidentId/diagnosis';
  static String incidentMatchmakingPath(int incidentId) =>
      '/incident/$incidentId/matchmaking';
  static String workshopRecommendationsPath(int incidentId) =>
      '/incident/$incidentId/recommendations';
  static String workshopRequestSentPath(int incidentId) =>
      '/incident/$incidentId/request-sent';
  static String serviceTrackingPath(int serviceId) =>
      '/services/$serviceId/tracking';
  static String servicePrequotationPath(int serviceId) =>
      '/services/$serviceId/prequotation';
  static String serviceFinalizationPath(int serviceId) =>
      '/services/$serviceId/finalization';
  static String servicePaymentPath(int serviceId) =>
      '/services/$serviceId/payment';
  static String serviceRatingPath(int serviceId) =>
      '/services/$serviceId/rating';
  static String operatorServicePath(int serviceId) =>
      '/operario/services/$serviceId';

  static String normalizeRole(String? role) {
    final normalized = (role ?? '').trim().toUpperCase();
    if (normalized == 'ADMIN') {
      return 'ADMINISTRADOR';
    }
    return normalized;
  }

  static bool isClientRole(String? role) => normalizeRole(role) == 'CLIENTE';

  static bool isOperatorRole(String? role) => normalizeRole(role) == 'OPERARIO';

  static bool isAdminRole(String? role) {
    final normalized = normalizeRole(role);
    return normalized == 'ADMINISTRADOR' ||
        normalized == 'ADMIN_SUCURSAL' ||
        normalized == 'ADMIN_GERENTE_SUCURSALES';
  }

  static String homeForRole(String? role) {
    if (isOperatorRole(role)) {
      return operatorHome;
    }
    if (isAdminRole(role)) {
      return adminMobileInfo;
    }
    return clientHome;
  }
}
