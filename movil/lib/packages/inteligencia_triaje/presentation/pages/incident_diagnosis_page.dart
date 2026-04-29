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
import '../../data/models/incident_classification_model.dart';
import '../../data/models/incident_detail_model.dart';
import '../controllers/incident_diagnosis_controller.dart';

class IncidentDiagnosisPage extends ConsumerStatefulWidget {
  const IncidentDiagnosisPage({super.key, required this.incidentId});

  final int incidentId;

  @override
  ConsumerState<IncidentDiagnosisPage> createState() =>
      _IncidentDiagnosisPageState();
}

class _IncidentDiagnosisPageState
    extends ConsumerState<IncidentDiagnosisPage> {
  bool _isRunning = false;
  IncidentClassificationModel? _lastClassification;
  _DiagnosisNotice? _notice;

  Future<void> _runDiagnosis() async {
    setState(() {
      _isRunning = true;
      _notice = null;
    });
    try {
      final classification = await ref
          .read(incidentDiagnosisProvider(widget.incidentId).notifier)
          .runDiagnosis(widget.incidentId);
      if (mounted) {
        setState(() => _lastClassification = classification);
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _notice = _mapDiagnosisNotice(error);
      });
    } finally {
      if (mounted) {
        setState(() => _isRunning = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(incidentDiagnosisProvider(widget.incidentId));
    final notifier =
        ref.read(incidentDiagnosisProvider(widget.incidentId).notifier);
    final classification = _lastClassification ?? notifier.lastClassification;

    return AppPageScaffold(
      label: 'DIAGNÓSTICO',
      title: 'Diagnóstico del incidente',
      subtitle:
          'Revisamos la información reportada para orientar la asistencia.',
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
        loading: () => const AppLoading(message: 'Cargando diagnóstico...'),
        error: (error, _) => AppErrorView(
          message: _mapDiagnosisError(error),
          onRetry: () => ref
              .read(incidentDiagnosisProvider(widget.incidentId).notifier)
              .refresh(widget.incidentId),
        ),
        data: (detail) => _DiagnosisContent(
          detail: detail,
          incidentId: widget.incidentId,
          classification: classification,
          notice: _notice,
          isRunning: _isRunning,
          onRunDiagnosis: _runDiagnosis,
        ),
      ),
    );
  }
}

class _DiagnosisContent extends StatelessWidget {
  const _DiagnosisContent({
    required this.detail,
    required this.incidentId,
    required this.classification,
    required this.notice,
    required this.isRunning,
    required this.onRunDiagnosis,
  });

  final IncidentDetailModel detail;
  final int incidentId;
  final IncidentClassificationModel? classification;
  final _DiagnosisNotice? notice;
  final bool isRunning;
  final VoidCallback onRunDiagnosis;

  String? get _severity => classification?.severity;
  double? get _confidence => classification?.confidence ?? detail.confidence;
  bool get _canGoToMatchmaking =>
      detail.isDiagnosed &&
      !detail.requiresManualReview &&
      detail.detectedSpecialty != null;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasDifferentSuggestion = detail.detectedSpecialty != null &&
        detail.detectedSpecialty!.idEspecialidad !=
            detail.reportedSpecialty.idEspecialidad;

    return ListView(
      children: [
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _InfoItem(
                label: 'Estado del incidente',
                value: _friendlyStatus(detail.status),
              ),
              _InfoItem(
                label: 'Sospecha inicial del cliente',
                value: detail.reportedSpecialty.nombre,
              ),
              if (detail.detectedSpecialty != null)
                _InfoItem(
                  label: 'Diagnóstico sugerido por IA',
                  value: detail.detectedSpecialty!.nombre,
                ),
              if (_severity != null)
                _InfoItem(label: 'Severidad', value: _severity!),
              if (_confidence != null)
                _InfoItem(
                  label: 'Confianza',
                  value: '${_confidence!.toStringAsFixed(1)}%',
                ),
              _InfoItem(
                label: 'Evidencias',
                value:
                    '${detail.imageCount} foto(s) y ${detail.audioCount} audio(s)',
              ),
              _InfoItem(
                label: 'Ubicación',
                value:
                    '${detail.latitud.toStringAsFixed(4)}, ${detail.longitud.toStringAsFixed(4)}',
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Descripción del incidente',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(
                detail.descripcionCliente,
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        if (detail.aiSummary != null && detail.aiSummary!.trim().isNotEmpty) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.smart_toy_outlined,
                      size: 20,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Resumen del diagnóstico',
                      style: theme.textTheme.titleMedium,
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  detail.aiSummary!,
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        ],
        if (hasDifferentSuggestion) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Text(
              'La IA encontró una posible causa distinta a la sospecha inicial.',
              style: theme.textTheme.bodyMedium,
            ),
          ),
        ],
        if (detail.requiresManualReview) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.warning_amber_rounded,
                  size: 24,
                  color: Colors.orange.shade700,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Este incidente requiere revisión manual antes de buscar talleres.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: Colors.orange.shade700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
        if (notice != null) ...[
          const SizedBox(height: 16),
          _DiagnosisNoticeCard(
            notice: notice!,
            onRetry: onRunDiagnosis,
            isLoading: isRunning,
          ),
        ],
        const SizedBox(height: 24),
        if (!detail.isDiagnosed) ...[
          AppCard(
            child: Text(
              'Usaremos la descripción, ubicación y evidencias para sugerir el tipo de asistencia.',
              style: theme.textTheme.bodyMedium,
            ),
          ),
          const SizedBox(height: 12),
          AppPrimaryButton(
            label: 'Generar diagnóstico',
            icon: Icons.analytics_outlined,
            isLoading: isRunning,
            onPressed: isRunning ? null : onRunDiagnosis,
          ),
        ],
        if (_canGoToMatchmaking)
          AppPrimaryButton(
            label: 'Buscar taller compatible',
            icon: Icons.storefront_outlined,
            onPressed: () =>
                context.push(AppRoutes.incidentMatchmakingPath(incidentId)),
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

  String _friendlyStatus(String status) {
    switch (status) {
      case 'EN_TRIAJE':
        return 'Analizando incidente';
      case 'DIAGNOSTICADO':
        return 'Diagnóstico listo';
      case 'EN_MATCHMAKING':
        return 'Buscando taller compatible';
      case 'EN_PROCESO':
        return 'En proceso';
      default:
        return localizeStatusLabel(status);
    }
  }
}

class _InfoItem extends StatelessWidget {
  const _InfoItem({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: theme.textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}

class _DiagnosisNotice {
  const _DiagnosisNotice({
    required this.title,
    required this.message,
  });

  final String title;
  final String message;
}

class _DiagnosisNoticeCard extends StatelessWidget {
  const _DiagnosisNoticeCard({
    required this.notice,
    required this.onRetry,
    required this.isLoading,
  });

  final _DiagnosisNotice notice;
  final VoidCallback onRetry;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            notice.title,
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            notice.message,
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          AppPrimaryButton(
            label: 'Intentar nuevamente',
            icon: Icons.refresh_rounded,
            isLoading: isLoading,
            onPressed: isLoading ? null : onRetry,
          ),
        ],
      ),
    );
  }
}

String _mapDiagnosisError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 404) {
      return 'No se encontró el incidente.';
    }
    if (error.statusCode == 409) {
      return 'El incidente aún no está listo para diagnóstico.';
    }
    if (error.statusCode == 502 || error.statusCode == 503) {
      return 'El diagnóstico por IA no está disponible en este momento.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró. Inicia sesión nuevamente.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo procesar el diagnóstico por un problema del servidor.';
    }
  }
  return 'No se pudo conectar con el servidor. Revisa tu conexión.';
}

_DiagnosisNotice _mapDiagnosisNotice(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 502 || error.statusCode == 503) {
      return const _DiagnosisNotice(
        title: 'Diagnóstico no disponible',
        message:
            'No pudimos generar el diagnóstico automático en este momento. Puedes intentar nuevamente más tarde.',
      );
    }
    if (error.statusCode == 409) {
      return const _DiagnosisNotice(
        title: 'Diagnóstico pendiente',
        message: 'El incidente aún no está listo para ser diagnosticado.',
      );
    }
  }
  return _DiagnosisNotice(
    title: 'No se pudo generar el diagnóstico',
    message: _mapDiagnosisError(error),
  );
}
