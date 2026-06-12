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
import '../../../../core/widgets/location_label.dart';
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

class _IncidentDiagnosisPageState extends ConsumerState<IncidentDiagnosisPage> {
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
    final notifier = ref.read(
      incidentDiagnosisProvider(widget.incidentId).notifier,
    );
    final classification = _lastClassification ?? notifier.lastClassification;

    return AppPageScaffold(
      label: 'DIAGNOSTICO',
      title: 'Diagnostico del incidente',
      subtitle:
          'Revisamos la informacion reportada para orientar la asistencia.',
      leading: IconButton(
        tooltip: 'Volver',
        onPressed: () => context.pop(),
        icon: const Icon(Icons.arrow_back_rounded),
      ),
      child: state.when(
        loading: () => const AppLoading(message: 'Analizando incidente...'),
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

  String? get _severity => classification?.severity ?? detail.severity;
  double? get _confidence => classification?.confidence ?? detail.confidence;
  String? get _summary => detail.aiSummary ?? classification?.summary;
  String? get _specificDiagnosis =>
      detail.specificDiagnosis ?? classification?.specificDiagnosis;
  String? get _suggestedService =>
      detail.suggestedService ?? classification?.suggestedService;
  String? get _customerRecommendation =>
      detail.customerRecommendation ?? classification?.customerRecommendation;
  String? get _operatorNotes =>
      detail.operatorNotes ?? classification?.operatorNotes;
  String? get _audioTranscript => detail.audioTranscript;
  String? get _audioSummary => detail.audioSummary;

  bool get _hasDiagnosisSections =>
      _specificDiagnosis != null ||
      _suggestedService != null ||
      _customerRecommendation != null ||
      _operatorNotes != null ||
      (_summary != null && _summary!.trim().isNotEmpty);

  bool get _canGoToMatchmaking =>
      detail.isDiagnosed && detail.detectedSpecialty != null;

  String? get _imageTechnicalMessage {
    if (!detail.isDiagnosed) {
      return null;
    }
    if (detail.imageCount <= 0 && detail.imageCountReceivedByBackend <= 0) {
      return null;
    }
    if (detail.imageEvidenceNotSentToAi) {
      return 'La IA no pudo analizar la imagen adjunta. Se usará diagnóstico general.';
    }
    if (detail.imageEvidenceAnalyzed) {
      return 'La imagen fue analizada para orientar el diagnóstico.';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasDifferentSuggestion =
        detail.detectedSpecialty != null &&
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
                value: localizeSpecialtyLabel(detail.reportedSpecialty.nombre),
              ),
              if (detail.detectedSpecialty != null)
                _InfoItem(
                  label: 'Especialidad detectada',
                  value: localizeSpecialtyLabel(
                    detail.detectedSpecialty!.nombre,
                  ),
                ),
              if (_severity != null)
                _InfoItem(
                  label: 'Severidad',
                  value: localizeStatusLabel(_severity),
                ),
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
                label: 'Ubicacion',
                valueWidget: LocationLabel(
                  latitud: detail.latitud,
                  longitud: detail.longitud,
                ),
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
                'Descripcion del incidente',
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
        const SizedBox(height: 16),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Transcripción del audio',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(
                _audioTranscript ?? 'No se adjuntó audio.',
                style: theme.textTheme.bodyMedium,
              ),
              if (_audioSummary != null && _audioSummary!.trim().isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(
                  _audioSummary!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
              if (detail.hasExperimentalAudioAnalysis) ...[
                const SizedBox(height: 12),
                Text(
                  'El audio no contiene voz clara. El análisis por sonido mecánico es experimental.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.error,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (_imageTechnicalMessage != null) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.image_search_outlined,
                  size: 22,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    _imageTechnicalMessage!,
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          ),
        ],
        if (_hasDiagnosisSections) ...[
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
                      'Diagnostico orientativo',
                      style: theme.textTheme.titleMedium,
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                if (_specificDiagnosis != null)
                  _DiagnosisSection(
                    title: 'Diagnóstico específico',
                    value: _specificDiagnosis!,
                  ),
                if (_suggestedService != null)
                  _DiagnosisSection(
                    title: 'Servicio sugerido',
                    value: _suggestedService!,
                  ),
                if (_customerRecommendation != null)
                  _DiagnosisSection(
                    title: 'Recomendacion para el cliente',
                    value: _customerRecommendation!,
                  ),
                if (_operatorNotes != null)
                  _DiagnosisSection(
                    title: 'Notas para el taller / operario',
                    value: _operatorNotes!,
                  ),
                if (_summary != null && _summary!.trim().isNotEmpty)
                  _DiagnosisSection(
                    title: 'Resumen final',
                    value: _summary!,
                    isLast: true,
                  ),
              ],
            ),
          ),
        ],
        if (hasDifferentSuggestion) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Text(
              'La IA encontro una posible causa distinta a la sospecha inicial.',
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
                  Icons.fact_check_outlined,
                  size: 24,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    (_confidence != null && _confidence! < 50)
                        ? 'La IA no tuvo suficiente confianza. Este resultado no es definitivo y requiere revisión manual.'
                        : 'Diagnóstico preliminar generado. El taller realizará una revisión física para confirmar la asistencia requerida.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface,
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
              'Usaremos la descripcion, ubicacion y evidencias para sugerir el tipo de asistencia.',
              style: theme.textTheme.bodyMedium,
            ),
          ),
          const SizedBox(height: 12),
          AppPrimaryButton(
            label: 'Generar diagnostico',
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
        return 'Diagnostico listo';
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
  const _InfoItem({required this.label, this.value, this.valueWidget});

  final String label;
  final String? value;
  final Widget? valueWidget;

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
          valueWidget ?? Text(value ?? '', style: theme.textTheme.bodyLarge),
        ],
      ),
    );
  }
}

class _DiagnosisSection extends StatelessWidget {
  const _DiagnosisSection({
    required this.title,
    required this.value,
    this.isLast = false,
  });

  final String title;
  final String value;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 6),
          Text(value, style: theme.textTheme.bodyLarge),
        ],
      ),
    );
  }
}

class _DiagnosisNotice {
  const _DiagnosisNotice({required this.title, required this.message});

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
          Text(notice.title, style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(notice.message, style: theme.textTheme.bodyMedium),
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
    final detail = _extractBackendDetail(error);
    final localizedDetail = localizeBackendMessage(detail);
    if (localizedDetail.isNotEmpty && localizedDetail != detail) {
      return localizedDetail;
    }
    if (detail.isNotEmpty) {
      return detail;
    }
    if (error.statusCode == 404) {
      return 'No se encontro el incidente.';
    }
    if (error.statusCode == 409) {
      return 'El incidente aun no esta listo para diagnostico.';
    }
    if (error.statusCode == 502 || error.statusCode == 503) {
      return 'El diagnostico por IA no esta disponible en este momento.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesion expiro. Inicia sesion nuevamente.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo procesar el diagnostico por un problema del servidor.';
    }
  }
  return 'No se pudo conectar con el servidor. Revisa tu conexion.';
}

_DiagnosisNotice _mapDiagnosisNotice(Object error) {
  if (error is ApiException) {
    final detail = _extractBackendDetail(error);
    final localizedDetail = localizeBackendMessage(detail);
    final backendMessage =
        localizedDetail.isNotEmpty && localizedDetail != detail
        ? localizedDetail
        : detail;
    if (error.statusCode == 502 || error.statusCode == 503) {
      return _DiagnosisNotice(
        title: 'Diagnostico no disponible',
        message: backendMessage.isNotEmpty
            ? backendMessage
            : 'No pudimos generar el diagnostico automatico en este momento. Puedes intentar nuevamente mas tarde.',
      );
    }
    if (error.statusCode == 409) {
      return _DiagnosisNotice(
        title: 'Diagnostico pendiente',
        message: backendMessage.isNotEmpty
            ? backendMessage
            : 'El incidente aun no esta listo para ser diagnosticado.',
      );
    }
  }
  return _DiagnosisNotice(
    title: 'No se pudo generar el diagnostico',
    message: _mapDiagnosisError(error),
  );
}

String _extractBackendDetail(ApiException error) {
  final details = error.details;
  if (details is String) {
    return details.trim();
  }
  if (details is Map<String, dynamic>) {
    final detail = details['detail'];
    if (detail is String) {
      return detail.trim();
    }
    if (detail is List) {
      return detail.map((item) => item.toString()).join(', ').trim();
    }
  }
  if (details is Map) {
    final detail = details['detail'];
    if (detail is String) {
      return detail.trim();
    }
    if (detail is List) {
      return detail.map((item) => item.toString()).join(', ').trim();
    }
  }
  return '';
}
