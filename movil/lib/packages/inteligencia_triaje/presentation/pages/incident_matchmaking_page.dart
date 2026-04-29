import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/utils/user_facing_text.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_error_view.dart';
import '../../../../core/widgets/app_loading.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/models/matchmaking_selection_model.dart';
import '../../data/models/matchmaking_status_model.dart';
import '../controllers/matchmaking_controller.dart';

class IncidentMatchmakingPage extends ConsumerStatefulWidget {
  const IncidentMatchmakingPage({super.key, required this.incidentId});

  final int incidentId;

  @override
  ConsumerState<IncidentMatchmakingPage> createState() =>
      _IncidentMatchmakingPageState();
}

class _IncidentMatchmakingPageState
    extends ConsumerState<IncidentMatchmakingPage> {
  bool _actionLoading = false;

  Future<void> _startMatchmaking() async {
    setState(() => _actionLoading = true);
    try {
      await ref
          .read(matchmakingProvider(widget.incidentId).notifier)
          .startMatchmaking(widget.incidentId);
    } catch (error) {
      _showError(_mapMatchmakingError(error));
    } finally {
      if (mounted) {
        setState(() => _actionLoading = false);
      }
    }
  }

  Future<void> _refreshStatus() async {
    setState(() => _actionLoading = true);
    try {
      await ref
          .read(matchmakingProvider(widget.incidentId).notifier)
          .loadStatus(widget.incidentId);
    } catch (error) {
      _showError(_mapMatchmakingError(error));
    } finally {
      if (mounted) {
        setState(() => _actionLoading = false);
      }
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(context).colorScheme.error,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(matchmakingProvider(widget.incidentId));

    return AppPageScaffold(
      label: 'BÚSQUEDA',
      title: 'Buscar taller compatible',
      subtitle:
          'El sistema seleccionará talleres según la falla y la ubicación.',
      actions: IconButton(
        tooltip: 'Volver',
        onPressed: () {
          if (Navigator.of(context).canPop()) {
            context.pop();
          } else {
            context.go(AppRoutes.clientHome);
          }
        },
        icon: const Icon(Icons.arrow_back_rounded),
      ),
      child: state.when(
        loading: () => const AppLoading(message: 'Buscando información...'),
        error: (error, _) => AppErrorView(
          message: _mapMatchmakingError(error),
          onRetry: _refreshStatus,
        ),
        data: (viewModel) => _MatchmakingContent(
          incidentId: widget.incidentId,
          selection: viewModel.selection,
          status: viewModel.status,
          isLoading: _actionLoading,
          onStart: _startMatchmaking,
          onRefresh: _refreshStatus,
        ),
      ),
    );
  }
}

class _MatchmakingContent extends StatelessWidget {
  const _MatchmakingContent({
    required this.incidentId,
    required this.selection,
    required this.status,
    required this.isLoading,
    required this.onStart,
    required this.onRefresh,
  });

  final int incidentId;
  final MatchmakingSelectionModel? selection;
  final MatchmakingStatusModel? status;
  final bool isLoading;
  final VoidCallback onStart;
  final VoidCallback onRefresh;

  bool get _hasWorkshop =>
      selection?.selectedWorkshop != null || status?.activeRequest != null;

  bool get _hasNoCandidate => selection?.noCandidate == true;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final workshop = selection?.selectedWorkshop ?? status?.activeRequest?.selectedWorkshop;
    final requestStatus = selection?.requestStatus ?? status?.activeRequest?.requestStatus;

    return ListView(
      children: [
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Usaremos el diagnóstico y tu ubicación para buscar talleres compatibles.',
                style: theme.textTheme.bodyLarge,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (selection == null && status == null) ...[
          AppPrimaryButton(
            label: 'Buscar taller',
            icon: Icons.search_rounded,
            isLoading: isLoading,
            onPressed: isLoading ? null : onStart,
          ),
        ] else if (_hasNoCandidate && !_hasWorkshop) ...[
          AppCard(
            child: Column(
              children: [
                Icon(
                  Icons.store_mall_directory_outlined,
                  size: 48,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(height: 12),
                Text(
                  'No hay talleres disponibles por ahora.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.titleMedium,
                ),
                if ((selection?.message ?? status?.message ?? '').trim().isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    localizeBackendMessage(
                      (selection?.message ?? status?.message ?? '').trim(),
                    ),
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          AppPrimaryButton(
            label: 'Volver al inicio',
            onPressed: () => context.go(AppRoutes.clientHome),
          ),
        ] else if (_hasWorkshop) ...[
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.check_circle_outline_rounded,
                      color: Colors.green.shade600,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Taller compatible encontrado',
                        style: theme.textTheme.titleMedium,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                if (workshop != null) ...[
                  _InfoRow(label: 'Taller', value: workshop.workshopName),
                  if (workshop.distanceKm != null)
                    _InfoRow(
                      label: 'Distancia',
                      value: '${workshop.distanceKm!.toStringAsFixed(1)} km',
                    ),
                  if (workshop.reputation != null)
                    _InfoRow(
                      label: 'Reputación',
                      value: '${workshop.reputation!.toStringAsFixed(1)} ★',
                    ),
                ],
                if (requestStatus != null)
                  _InfoRow(
                    label: 'Estado de solicitud',
                    value: localizeStatusLabel(requestStatus),
                  ),
                const SizedBox(height: 8),
                Text(
                  _compatibilityLabel(selection, status),
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          AppPrimaryButton(
            label: 'Ver talleres recomendados',
            icon: Icons.recommend_rounded,
            onPressed: () =>
                context.push(AppRoutes.workshopRecommendationsPath(incidentId)),
          ),
        ],
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: isLoading ? null : onRefresh,
            child: const Text('Actualizar estado'),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () => context.go(AppRoutes.clientHome),
            child: const Text('Volver al inicio'),
          ),
        ),
        const SizedBox(height: 24),
      ],
    );
  }

  String _compatibilityLabel(
    MatchmakingSelectionModel? selection,
    MatchmakingStatusModel? status,
  ) {
    final totalScore = selection?.totalScore ?? status?.activeRequest?.totalScore;
    if (totalScore == null) {
      return 'Compatibilidad confirmada según la falla reportada y tu ubicación.';
    }
    if (totalScore >= 80) {
      return 'Compatibilidad alta para este incidente.';
    }
    if (totalScore >= 60) {
      return 'Compatibilidad adecuada para este incidente.';
    }
    return 'Se encontró una opción disponible para tu incidente.';
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 118,
            child: Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: Text(value, style: theme.textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

String _mapMatchmakingError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 404) {
      return 'No se encontró el incidente.';
    }
    if (error.statusCode == 409) {
      return 'El incidente aún no está listo para buscar talleres.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró. Inicia sesión nuevamente.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo buscar un taller por un problema del servidor.';
    }
  }
  return 'No se pudo conectar con el servidor. Revisa tu conexión.';
}
