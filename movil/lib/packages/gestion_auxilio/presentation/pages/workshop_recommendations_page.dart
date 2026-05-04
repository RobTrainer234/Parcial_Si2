import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/utils/user_facing_text.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_empty_view.dart';
import '../../../../core/widgets/app_error_view.dart';
import '../../../../core/widgets/app_loading.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/models/incident_recommendations_model.dart';
import '../../data/models/recommended_workshop_model.dart';
import '../controllers/recommendations_controller.dart';

class WorkshopRecommendationsPage extends ConsumerStatefulWidget {
  const WorkshopRecommendationsPage({super.key, required this.incidentId});

  final int incidentId;

  @override
  ConsumerState<WorkshopRecommendationsPage> createState() =>
      _WorkshopRecommendationsPageState();
}

class _WorkshopRecommendationsPageState
    extends ConsumerState<WorkshopRecommendationsPage> {
  int? _hiringWorkshopId;

  Future<void> _hireWorkshop(int workshopId) async {
    setState(() => _hiringWorkshopId = workshopId);
    try {
      final result = await ref
          .read(recommendationsProvider(widget.incidentId).notifier)
          .hireWorkshop(workshopId);
      if (mounted) {
        context.go(
          AppRoutes.workshopRequestSentPath(widget.incidentId),
          extra: result,
        );
      }
    } catch (error) {
      _showError(_mapHireError(error));
    } finally {
      if (mounted) {
        setState(() => _hiringWorkshopId = null);
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
    final state = ref.watch(recommendationsProvider(widget.incidentId));

    return AppPageScaffold(
      label: 'TALLERES',
      title: 'Talleres recomendados',
      subtitle: 'Elige el taller que deseas solicitar para tu auxilio.',
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
        loading: () => const AppLoading(message: 'Cargando recomendaciones...'),
        error: (error, _) => AppErrorView(
          message: _mapRecommendationsError(error),
          onRetry: () => ref
              .read(recommendationsProvider(widget.incidentId).notifier)
              .loadRecommendations(widget.incidentId),
        ),
        data: (data) => _RecommendationsContent(
          data: data,
          incidentId: widget.incidentId,
          hiringWorkshopId: _hiringWorkshopId,
          onRetry: () => ref
              .read(recommendationsProvider(widget.incidentId).notifier)
              .loadRecommendations(widget.incidentId),
          onHire: _hireWorkshop,
        ),
      ),
    );
  }
}

class _RecommendationsContent extends StatelessWidget {
  const _RecommendationsContent({
    required this.data,
    required this.incidentId,
    required this.hiringWorkshopId,
    required this.onRetry,
    required this.onHire,
  });

  final IncidentRecommendationsModel data;
  final int incidentId;
  final int? hiringWorkshopId;
  final VoidCallback onRetry;
  final ValueChanged<int> onHire;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (!data.hasRecommendations || data.recommendedWorkshops.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const AppEmptyView(
              message: 'No hay talleres recomendados por ahora.',
            ),
            const SizedBox(height: 16),
            OutlinedButton(
              onPressed: onRetry,
              child: const Text('Reintentar'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () => context.go(AppRoutes.clientHome),
              child: const Text('Volver al inicio'),
            ),
          ],
        ),
      );
    }

    return ListView(
      children: [
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Diagnóstico del incidente',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 10),
              if (data.diagnosis.detectedSpecialty != null)
                _InfoRow(
                  label: 'Especialidad detectada',
                  value: localizeSpecialtyLabel(data.diagnosis.detectedSpecialty),
                ),
              if (data.diagnosis.severity != null)
                _InfoRow(
                  label: 'Severidad',
                  value: localizeStatusLabel(data.diagnosis.severity),
                ),
              if (data.diagnosis.confidence != null)
                _InfoRow(
                  label: 'Confianza',
                  value: '${data.diagnosis.confidence!.toStringAsFixed(1)}%',
                ),
              if (data.diagnosis.aiSummary != null &&
                  data.diagnosis.aiSummary!.trim().isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  data.diagnosis.aiSummary!,
                  style: theme.textTheme.bodyMedium,
                ),
              ],
              if (data.diagnosis.requiresManualReview) ...[
                const SizedBox(height: 12),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.warning_amber_rounded,
                      size: 22,
                      color: Colors.orange.shade700,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'La IA no tiene certeza completa. El taller realizará diagnóstico físico.',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: Colors.orange.shade700,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        ...data.recommendedWorkshops.map(
          (workshop) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: _RecommendedWorkshopCard(
              workshop: workshop,
              isTop: workshop.workshopId == data.topRecommendationWorkshopId,
              isHiring: hiringWorkshopId == workshop.workshopId,
              onHire: () => onHire(workshop.workshopId),
            ),
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
}

class _RecommendedWorkshopCard extends StatelessWidget {
  const _RecommendedWorkshopCard({
    required this.workshop,
    required this.isTop,
    required this.isHiring,
    required this.onHire,
  });

  final RecommendedWorkshopModel workshop;
  final bool isTop;
  final bool isHiring;
  final VoidCallback onHire;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.storefront_rounded,
                size: 22,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  workshop.workshopName,
                  style: theme.textTheme.titleMedium,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (isTop) const Chip(label: Text('Recomendado')),
              if (workshop.insuranceCoveringThisSpecialty)
                const Chip(label: Text('Cobertura activa')),
              if (workshop.insurancePriorityApplied)
                const Chip(label: Text('Prioridad seguro')),
            ],
          ),
          const SizedBox(height: 12),
          _InfoRow(
            label: 'Distancia',
            value: '${workshop.distanceKm.toStringAsFixed(1)} km',
          ),
          if (workshop.estimatedArrivalText != null)
            _InfoRow(
              label: 'Llegada estimada',
              value: workshop.estimatedArrivalText!,
            ),
          if (workshop.reputation != null)
            _InfoRow(
              label: 'Reputación',
              value: '${workshop.reputation!.toStringAsFixed(1)} ★',
            ),
          if (workshop.estimatedCost != null)
            _InfoRow(
              label: 'Costo estimado',
              value:
                  '${workshop.estimatedCost!.toStringAsFixed(2)} ${workshop.currency ?? 'BOB'}',
            ),
          if (workshop.coverageName != null)
            _InfoRow(label: 'Cobertura', value: workshop.coverageName!),
          const SizedBox(height: 12),
          AppPrimaryButton(
            label: 'Solicitar auxilio',
            icon: Icons.handshake_outlined,
            isLoading: isHiring,
            onPressed: isHiring ? null : onHire,
          ),
        ],
      ),
    );
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
            width: 128,
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

String _mapRecommendationsError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 409) {
      final detail = error.details?.toString().toLowerCase() ?? '';
      if (detail.contains('diagnosis')) {
        return 'Primero debe completarse el diagnóstico del incidente.';
      }
      return 'Las recomendaciones todavía no están listas.';
    }
    if (error.statusCode == 404) {
      return 'No se encontró el incidente.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró. Inicia sesión nuevamente.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudieron cargar las recomendaciones.';
    }
  }
  return 'No se pudo conectar con el servidor. Revisa tu conexión.';
}

String _mapHireError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 409) {
      final detail = error.details?.toString().toLowerCase() ?? '';
      if (detail.contains('active') || detail.contains('solicitud activa')) {
        return 'Ya existe una solicitud activa para este incidente.';
      }
      return 'El taller seleccionado ya no está disponible para este incidente.';
    }
    if (error.statusCode == 404) {
      return 'No se encontró el incidente.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró. Inicia sesión nuevamente.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo enviar la solicitud al taller.';
    }
  }
  return 'No se pudo conectar con el servidor. Revisa tu conexión.';
}
