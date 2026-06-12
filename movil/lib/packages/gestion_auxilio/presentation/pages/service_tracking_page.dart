import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/auth/auth_controller.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/realtime/service_realtime_socket.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/utils/user_facing_text.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_error_view.dart';
import '../../../../core/widgets/app_loading.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../controllers/service_tracking_controller.dart';
import '../widgets/service_tracking_map.dart';

class ServiceTrackingPage extends ConsumerStatefulWidget {
  const ServiceTrackingPage({
    super.key,
    required this.serviceId,
  });

  final int serviceId;

  @override
  ConsumerState<ServiceTrackingPage> createState() =>
      _ServiceTrackingPageState();
}

class _ServiceTrackingPageState extends ConsumerState<ServiceTrackingPage> {
  Timer? _refreshTimer;
  ServiceRealtimeSocketSession? _realtimeSession;
  StreamSubscription<ServiceRealtimeEvent>? _realtimeEventSubscription;
  StreamSubscription<ServiceRealtimeConnectionState>? _realtimeStateSubscription;
  ServiceRealtimeConnectionState _realtimeState =
      ServiceRealtimeConnectionState.disconnected;
  DateTime? _lastRealtimeEventAt;
  bool _showHistory = false;
  bool _dismissedRatingBanner = false;
  int _previousEta = -1;
  String? _previousState;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(const Duration(minutes: 1), (_) {
      if (!mounted) return;
      ref
          .read(serviceTrackingProvider(widget.serviceId).notifier)
          .refreshSilently();
    });
    _connectRealtime();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _realtimeEventSubscription?.cancel();
    _realtimeStateSubscription?.cancel();
    _realtimeSession?.dispose();
    super.dispose();
  }

  void _connectRealtime() {
    final token = ref.read(authControllerProvider).valueOrNull?.accessToken;
    if (token == null || token.isEmpty) {
      return;
    }
    final realtimeService = ref.read(serviceRealtimeSocketServiceProvider);
    final session = realtimeService.connectToService(
      serviceId: widget.serviceId,
      token: token,
    );
    _realtimeSession = session;
    _realtimeEventSubscription = session.events.listen((event) {
      ref
          .read(serviceTrackingProvider(widget.serviceId).notifier)
          .applyRealtimeEvent(event);
      if (mounted) {
        setState(() {
          _lastRealtimeEventAt = DateTime.now();
        });
      }
    });
    _realtimeStateSubscription = session.states.listen((nextState) {
      if (mounted) {
        setState(() {
          _realtimeState = nextState;
        });
      }
    });
  }

  String _realtimeStatusLabel() {
    switch (_realtimeState) {
      case ServiceRealtimeConnectionState.connected:
        return 'En vivo';
      case ServiceRealtimeConnectionState.reconnecting:
        return 'Reconectando';
      case ServiceRealtimeConnectionState.disconnected:
        if (_lastRealtimeEventAt == null) {
          return 'Sin conexion en tiempo real';
        }
        return 'Actualizado ${_realtimeElapsedLabel(_lastRealtimeEventAt)}';
    }
  }

  String _formatEta(int? seconds) {
    if (seconds == null || seconds <= 0) return 'Llegando...';
    if (seconds < 60) return '${seconds}s';
    final minutes = (seconds / 60).ceil();
    if (minutes < 60) return '$minutes min';
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return '${hours}h ${mins}min';
  }

  Color _stateColor(String? state) {
    switch (state) {
      case 'EN_ESPERA_ASIGNACION':
        return Colors.orange;
      case 'ASIGNADO':
      case 'EN_CAMINO':
        return Colors.blue;
      case 'EN_SITIO':
      case 'EN_DIAGNOSTICO_FISICO':
      case 'EN_REPARACION':
        return Colors.deepPurple;
      case 'COMPLETADO_PENDIENTE_CONFIRMACION':
        return Colors.teal;
      case 'FINALIZADO_PENDIENTE_PAGO':
        return Colors.amber.shade700;
      case 'PAGADO':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(serviceTrackingProvider(widget.serviceId));

    return AppPageScaffold(
      label: 'SEGUIMIENTO',
      title: 'Seguimiento del servicio',
      subtitle: 'Consulta el avance de tu asistencia.',
      leading: IconButton(
        tooltip: 'Volver',
        onPressed: () => context.pop(),
        icon: const Icon(Icons.arrow_back_rounded),
      ),
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: () => ref
            .read(serviceTrackingProvider(widget.serviceId).notifier)
            .refresh(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      padding: EdgeInsets.zero,
      child: state.when(
        loading: () => const AppLoading(message: 'Cargando seguimiento...'),
        error: (error, _) => AppErrorView(
          message: _mapTrackingError(error),
          onRetry: () => ref
              .read(serviceTrackingProvider(widget.serviceId).notifier)
              .refresh(),
        ),
        data: (data) {
          final status = data.status;
          final validHistory = data.history
              .where(
                (point) => point.latitud != null && point.longitud != null,
              )
              .toList();
          final recentHistory = validHistory.length <= 5
              ? validHistory.reversed.toList()
              : validHistory.reversed.take(5).toList();

          final hasLiveLocation = status.hasLiveLocation == true;
          final isStale = status.locationStale == true;
          final arrived = status.serviceState == 'EN_SITIO';
          final operatorCoordsAvailable =
              status.lastOperarioLatitud != null &&
                  status.lastOperarioLongitud != null;

          final etaSeconds = status.etaSeconds;
          if (etaSeconds != null && etaSeconds != _previousEta) {
            _previousEta = etaSeconds;
          }

          final currentState = status.serviceState;
          if (currentState != _previousState && _previousState != null) {
            HapticFeedback.mediumImpact();
            SystemSound.play(SystemSoundType.alert);
          }
          _previousState = currentState;

          return RefreshIndicator(
            onRefresh: () => ref
                .read(serviceTrackingProvider(widget.serviceId).notifier)
                .refresh(),
            child: ListView(
              children: [
                AppCard(
                  child: Text(_realtimeStatusLabel()),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  height: 340,
                  child: Stack(
                    children: [
                      ServiceTrackingMap(
                        incidentLatitud: status.incidentLatitud,
                        incidentLongitud: status.incidentLongitud,
                        operarioLatitud: status.lastOperarioLatitud,
                        operarioLongitud: status.lastOperarioLongitud,
                        historyPoints: validHistory,
                        lastLocationAt: status.lastLocationAt,
                        routePoints: status.routePoints,
                        hasArrived: arrived,
                      ),
                      Positioned(
                        left: 16,
                        right: 16,
                        bottom: 16,
                        child: _EtaCard(
                          etaSeconds: etaSeconds,
                          etaText: status.etaText,
                          distanceMeters: status.currentDistanceMeters,
                          formatEta: _formatEta,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: _StatusCard(
                    stateColor: _stateColor(status.serviceState),
                    serviceState: status.serviceState,
                    hasLiveLocation: hasLiveLocation,
                    isStale: isStale,
                    operatorCoordsAvailable: operatorCoordsAvailable,
                    trackingMessage: _trackingMessage(
                      status.serviceState,
                      status,
                    ),
                    arrived: arrived,
                  ),
                ),
                if (arrived) ...[
                  const SizedBox(height: 12),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: _ArrivalCelebration(),
                  ),
                ],
                if (status.serviceState == 'PAGADO' &&
                    !_dismissedRatingBanner) ...[
                  const SizedBox(height: 12),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: _RatingBanner(
                      serviceId: widget.serviceId,
                      onDismiss: () =>
                          setState(() => _dismissedRatingBanner = true),
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: _ActionButtons(
                    serviceState: status.serviceState,
                    serviceId: widget.serviceId,
                    hasLiveLocation: hasLiveLocation,
                    arrived: arrived,
                  ),
                ),
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Ubicacion del operario',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        if (_hasLastLocation(status)) ...[
                          Text(
                            'Ultima ubicacion registrada',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${status.lastOperarioLatitud!.toStringAsFixed(5)}, ${status.lastOperarioLongitud!.toStringAsFixed(5)}',
                          ),
                          if (status.lastLocationAt != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              'Actualizada: ${_formatDate(status.lastLocationAt)}',
                            ),
                          ],
                          if (status.currentDistanceMeters != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              'Distancia aproximada: ${(status.currentDistanceMeters! / 1000).toStringAsFixed(2)} km',
                            ),
                          ],
                          if (status.etaText != null) ...[
                            const SizedBox(height: 4),
                            Text('ETA: ${status.etaText}'),
                          ],
                        ] else
                          const Text(
                            'Aun no hay ubicacion en tiempo real del operario.',
                          ),
                      ],
                    ),
                  ),
                ),
                if (recentHistory.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: InkWell(
                      onTap: () => setState(() => _showHistory = !_showHistory),
                      child: AppCard(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 14,
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.timeline,
                              size: 20,
                              color: theme.colorScheme.primary,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'Historial de ubicación',
                                style: theme.textTheme.titleSmall,
                              ),
                            ),
                            Text(
                              '${recentHistory.length} puntos',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Icon(
                              _showHistory
                                  ? Icons.expand_less
                                  : Icons.expand_more,
                              size: 20,
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  if (_showHistory)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: AppCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            ...recentHistory.map(
                              (point) => Padding(
                                padding: const EdgeInsets.only(bottom: 10),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Icon(
                                      Icons.circle,
                                      size: 8,
                                      color: theme.colorScheme.primary,
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            '${point.latitud!.toStringAsFixed(5)}, ${point.longitud!.toStringAsFixed(5)}',
                                            style: theme.textTheme.bodySmall,
                                          ),
                                          Text(
                                            _formatDate(point.fechaHora),
                                            style: theme.textTheme.bodySmall
                                                ?.copyWith(
                                              color: theme.colorScheme
                                                  .onSurfaceVariant,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
                const SizedBox(height: 24),
              ],
            ),
          );
        },
      ),
    );
  }

  String _trackingMessage(String serviceState, dynamic status) {
    switch (serviceState) {
      case 'EN_ESPERA_ASIGNACION':
        return 'El taller aceptó tu solicitud. Estamos asignando un operario.';
      case 'COMPLETADO_PENDIENTE_CONFIRMACION':
        return 'El servicio fue completado y está pendiente de tu validación.';
      case 'FINALIZADO_PENDIENTE_PAGO':
        return 'La resolución fue confirmada. El servicio está pendiente de pago.';
      case 'PAGADO':
        return 'Tu asistencia fue completada y pagada correctamente.';
    }
    if (status.hasLiveLocation == true) {
      return 'Ubicación del operario disponible en tiempo real.';
    }
    if (status.locationStale == true) {
      return 'La ubicación del operario puede estar desactualizada.';
    }
    return 'Aún no hay ubicación en tiempo real del operario.';
  }
}

class _EtaCard extends StatelessWidget {
  final int? etaSeconds;
  final String? etaText;
  final double? distanceMeters;
  final String Function(int?) formatEta;

  const _EtaCard({
    required this.etaSeconds,
    required this.etaText,
    required this.distanceMeters,
    required this.formatEta,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasEta = etaSeconds != null && etaSeconds! > 0;
    final hasDistance = distanceMeters != null && distanceMeters! > 0;

    return Material(
      elevation: 6,
      borderRadius: BorderRadius.circular(16),
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.directions_car_rounded,
                color: Colors.blue.shade700,
                size: 24,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 400),
                    transitionBuilder: (child, anim) => FadeTransition(
                      opacity: anim,
                      child: SizeTransition(
                        sizeFactor: anim,
                        child: child,
                      ),
                    ),
                    child: Text(
                      hasEta ? formatEta(etaSeconds) : 'Calculando...',
                      key: ValueKey('eta_$etaSeconds'),
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                  ),
                  if (hasDistance) ...[
                    const SizedBox(height: 2),
                    Text(
                      '${(distanceMeters! / 1000).toStringAsFixed(1)} km de distancia',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (etaText != null && etaText!.isNotEmpty)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  etaText!,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: Colors.green.shade700,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  final Color stateColor;
  final String serviceState;
  final bool hasLiveLocation;
  final bool isStale;
  final bool operatorCoordsAvailable;
  final String trackingMessage;
  final bool arrived;

  const _StatusCard({
    required this.stateColor,
    required this.serviceState,
    required this.hasLiveLocation,
    required this.isStale,
    required this.operatorCoordsAvailable,
    required this.trackingMessage,
    required this.arrived,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: 6,
            decoration: BoxDecoration(
              color: stateColor,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(16),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(18),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: stateColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    arrived
                        ? Icons.check_circle_outline
                        : hasLiveLocation
                            ? Icons.gps_fixed
                            : Icons.location_searching,
                    color: stateColor,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: stateColor.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              _friendlyState(serviceState),
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: stateColor,
                              ),
                            ),
                          ),
                          const Spacer(),
                          if (hasLiveLocation)
                            _LiveIndicator(isStale: isStale),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        trackingMessage,
                        style: theme.textTheme.bodyMedium,
                      ),
                      if (arrived) ...[
                        const SizedBox(height: 10),
                        Text(
                          'El operario está en el lugar del incidente.',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: Colors.green.shade700,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                      if (!operatorCoordsAvailable && !arrived) ...[
                        const SizedBox(height: 10),
                        Text(
                          'Esperando ubicación del operario...',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LiveIndicator extends StatelessWidget {
  final bool isStale;
  const _LiveIndicator({required this.isStale});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isStale ? Colors.orange.shade50 : Colors.green.shade50,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isStale ? Colors.orange : Colors.green,
            ),
          ),
          const SizedBox(width: 4),
          Text(
            isStale ? 'Desactualizada' : 'En vivo',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: isStale ? Colors.orange.shade700 : Colors.green.shade700,
            ),
          ),
        ],
      ),
    );
  }
}

class _ArrivalCelebration extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.green.shade500, Colors.green.shade700],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.green.shade400.withValues(alpha: 0.3),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(
              Icons.celebration_outlined,
              color: Colors.white,
              size: 32,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '¡El operario llegó!',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Está en el lugar del incidente para atenderte.',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.9),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RatingBanner extends StatefulWidget {
  final int serviceId;
  final VoidCallback onDismiss;

  const _RatingBanner({
    required this.serviceId,
    required this.onDismiss,
  });

  @override
  State<_RatingBanner> createState() => _RatingBannerState();
}

class _RatingBannerState extends State<_RatingBanner>
    with SingleTickerProviderStateMixin {
  late final AnimationController _animController;
  late final Animation<Offset> _slideAnim;
  late final Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.3),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOutCubic,
    ));
    _fadeAnim = Tween<double>(begin: 0, end: 1).animate(CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOut,
    ));
    _animController.forward();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  void _dismiss() {
    _animController.reverse().then((_) {
      if (mounted) widget.onDismiss();
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SlideTransition(
      position: _slideAnim,
      child: FadeTransition(
        opacity: _fadeAnim,
        child: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                Colors.amber.shade400,
                Colors.orange.shade500,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.orange.shade400.withValues(alpha: 0.3),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.25),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: const Icon(
                        Icons.star_rounded,
                        color: Colors.white,
                        size: 28,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Servicio completado',
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: Colors.white.withValues(alpha: 0.8),
                              fontWeight: FontWeight.w500,
                              letterSpacing: 0.5,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '¿Cómo fue tu experiencia?',
                            style: theme.textTheme.titleMedium?.copyWith(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  'Tu opinión nos ayuda a mejorar el servicio.',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.9),
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: SizedBox(
                        height: 44,
                        child: ElevatedButton.icon(
                          onPressed: () {
                            context.push(
                              AppRoutes.serviceRatingPath(widget.serviceId),
                            );
                          },
                          icon: const Icon(Icons.star_rounded, size: 18),
                          label: const Text('Calificar'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: Colors.orange.shade700,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                            elevation: 0,
                            textStyle: const TextStyle(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    SizedBox(
                      height: 44,
                      child: OutlinedButton(
                        onPressed: _dismiss,
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.white,
                          side: BorderSide(
                            color: Colors.white.withValues(alpha: 0.5),
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                          textStyle: const TextStyle(
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        child: const Text('Ahora no'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ActionButtons extends StatelessWidget {
  final String serviceState;
  final int serviceId;
  final bool hasLiveLocation;
  final bool arrived;

  const _ActionButtons({
    required this.serviceState,
    required this.serviceId,
    required this.hasLiveLocation,
    required this.arrived,
  });

  @override
  Widget build(BuildContext context) {
    final actions = <Widget>[];

    if (serviceState == 'COMPLETADO_PENDIENTE_CONFIRMACION') {
      actions.add(
        _ActionButton(
          label: 'Validar resolución',
          icon: Icons.verified_outlined,
          onPressed: () => context.push(
            AppRoutes.serviceFinalizationPath(serviceId),
          ),
        ),
      );
    }
    if (serviceState == 'FINALIZADO_PENDIENTE_PAGO') {
      actions.add(
        _ActionButton(
          label: 'Pagar servicio',
          icon: Icons.payments_outlined,
          onPressed: () => context.push(
            AppRoutes.servicePaymentPath(serviceId),
          ),
        ),
      );
    }
    if (serviceState == 'PAGADO') {
      actions.add(
        _ActionButton(
          label: 'Calificar servicio',
          icon: Icons.star_outline,
          onPressed: () => context.push(
            AppRoutes.serviceRatingPath(serviceId),
          ),
        ),
      );
    }

    actions.add(
      _ActionButton(
        label: 'Ver pre-cotización',
        icon: Icons.receipt_outlined,
        onPressed: () => context.push(
          AppRoutes.servicePrequotationPath(serviceId),
        ),
      ),
    );

    if (actions.length > 2) {
      return Wrap(
        spacing: 8,
        runSpacing: 8,
        children: actions,
      );
    }

    return Row(
      children: [
        if (actions.isNotEmpty) Expanded(child: actions.first),
        if (actions.length > 1) ...[
          const SizedBox(width: 8),
          Expanded(child: actions[1]),
        ],
      ],
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onPressed;

  const _ActionButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 18),
        label: Text(label),
      ),
    );
  }
}

bool _hasLastLocation(dynamic status) {
  return status.lastOperarioLatitud != null &&
      status.lastOperarioLongitud != null;
}

String _friendlyState(String state) {
  switch (state) {
    case 'EN_ESPERA_ASIGNACION':
      return 'En espera de asignación';
    case 'ASIGNADO':
      return 'Asignado';
    case 'EN_CAMINO':
      return 'En camino';
    case 'EN_SITIO':
      return 'En sitio';
    case 'EN_DIAGNOSTICO_FISICO':
      return 'Diagnóstico físico';
    case 'EN_REPARACION':
      return 'En reparación';
    case 'ESPERANDO_REPUESTOS':
      return 'Esperando repuestos';
    case 'COMPLETADO_PENDIENTE_CONFIRMACION':
      return 'Pendiente de confirmación';
    case 'FINALIZADO_PENDIENTE_PAGO':
      return 'Pendiente de pago';
    case 'PAGADO':
      return 'Pagado';
    default:
      return localizeStatusLabel(state);
  }
}

String _realtimeElapsedLabel(DateTime? value) {
  if (value == null) {
    return 'sin actualizaciones recientes';
  }
  final difference = DateTime.now().difference(value);
  if (difference.inSeconds < 60) {
    return 'hace ${difference.inSeconds}s';
  }
  if (difference.inMinutes < 60) {
    return 'hace ${difference.inMinutes} min';
  }
  return 'hace ${difference.inHours} h';
}

String _mapTrackingError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 404) return 'No se encontró el servicio.';
    if (error.statusCode == 409) {
      return 'El seguimiento en tiempo real aún no está disponible.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró. Inicia sesión nuevamente.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo cargar el seguimiento.';
    }
  }
  return 'No se pudo conectar con el servidor.';
}

String _formatDate(DateTime? value) {
  if (value == null) return 'Fecha no disponible';
  final localValue = value.toLocal();
  return '${localValue.day.toString().padLeft(2, '0')}/'
      '${localValue.month.toString().padLeft(2, '0')}/'
      '${localValue.year} '
      '${localValue.hour.toString().padLeft(2, '0')}:'
      '${localValue.minute.toString().padLeft(2, '0')}';
}
