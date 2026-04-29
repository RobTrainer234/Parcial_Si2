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
import '../../../gestion_auxilio/data/models/client_active_service_model.dart';
import '../../../gestion_auxilio/presentation/controllers/active_services_controller.dart';
import '../../data/models/existing_rating_model.dart';
import '../../data/models/rating_target_model.dart';
import '../../data/models/rating_status_model.dart';
import '../controllers/rating_controller.dart';

class ServiceRatingPage extends ConsumerStatefulWidget {
  const ServiceRatingPage({
    super.key,
    required this.serviceId,
  });

  final int serviceId;

  @override
  ConsumerState<ServiceRatingPage> createState() => _ServiceRatingPageState();
}

class _ServiceRatingPageState extends ConsumerState<ServiceRatingPage> {
  static const int _commentMaxLength = 2000;

  final Map<String, int> _starsByTarget = {};
  final Map<String, TextEditingController> _commentControllers = {};
  final Set<String> _submittingTargets = {};

  @override
  void dispose() {
    for (final controller in _commentControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ratingState = ref.watch(ratingControllerProvider(widget.serviceId));
    final activeServices = ref.watch(activeServicesProvider).valueOrNull;
    final serviceSummary = _findServiceSummary(activeServices, widget.serviceId);

    return AppPageScaffold(
      label: 'CALIFICACIÓN',
      title: 'Calificar servicio',
      subtitle: 'Evalúa la atención recibida.',
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: () =>
            ref.read(ratingControllerProvider(widget.serviceId).notifier).refresh(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      child: ratingState.when(
        loading: () => const AppLoading(message: 'Cargando calificación...'),
        error: (error, _) => AppErrorView(
          message: _mapRatingError(error),
          onRetry: () =>
              ref.read(ratingControllerProvider(widget.serviceId).notifier).refresh(),
        ),
        data: (data) {
          for (final target in data.allowedTargets) {
            final key = _targetKey(target.targetType, target.targetId);
            final existing = _findExistingRating(
              data.existingRatings,
              target.targetType,
              target.targetId,
            );
            _starsByTarget.putIfAbsent(key, () => existing?.stars ?? 0);
            _commentControllers.putIfAbsent(
              key,
              () => TextEditingController(text: existing?.comment ?? ''),
            );
          }

          final allRated = data.allowedTargets.isNotEmpty &&
              data.allowedTargets.every(
                (target) => _findExistingRating(
                      data.existingRatings,
                      target.targetType,
                      target.targetId,
                    ) !=
                    null,
              );

          return RefreshIndicator(
            onRefresh: () =>
                ref.read(ratingControllerProvider(widget.serviceId).notifier).refresh(),
            child: ListView(
              children: [
                _ServiceSummaryCard(
                  data: data,
                  serviceSummary: serviceSummary,
                ),
                const SizedBox(height: 16),
                if (data.allowedTargets.isEmpty)
                  const AppEmptyView(
                    message: 'No hay elementos disponibles para calificar.',
                  )
                else
                  ...data.allowedTargets.map(
                    (target) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _buildTargetCard(
                        context,
                        data.existingRatings,
                        target,
                      ),
                    ),
                  ),
                if (allRated)
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Ya calificaste este servicio.',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Tus calificaciones ya fueron registradas. Si deseas, puedes actualizarlas desde esta misma pantalla porque el backend lo permite.',
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            OutlinedButton(
                              onPressed: () => context.go(
                                AppRoutes.serviceTrackingPath(widget.serviceId),
                              ),
                              child: const Text('Ver seguimiento'),
                            ),
                            OutlinedButton(
                              onPressed: () => context.go(AppRoutes.clientHome),
                              child: const Text('Volver al inicio'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 16),
                if (!allRated)
                  OutlinedButton(
                    onPressed: () =>
                        context.go(AppRoutes.serviceTrackingPath(widget.serviceId)),
                    child: const Text('Volver al seguimiento'),
                  ),
                const SizedBox(height: 8),
                OutlinedButton(
                  onPressed: () => context.go(AppRoutes.clientHome),
                  child: const Text('Volver al inicio'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildTargetCard(
    BuildContext context,
    List<ExistingRatingModel> existingRatings,
    RatingTargetModel target,
  ) {
    final key = _targetKey(target.targetType, target.targetId);
    final controller = _commentControllers[key]!;
    final stars = _starsByTarget[key] ?? 0;
    final existing =
        _findExistingRating(existingRatings, target.targetType, target.targetId);
    final isSubmitting = _submittingTargets.contains(key);

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  target.label,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              if (existing != null)
                const Chip(
                  label: Text('Ya calificado'),
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Tu calificación: ${stars > 0 ? stars : '-'} de 5',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 4,
            children: List.generate(5, (index) {
              final value = index + 1;
              return IconButton(
                onPressed: isSubmitting
                    ? null
                    : () => setState(() => _starsByTarget[key] = value),
                visualDensity: VisualDensity.compact,
                icon: Icon(
                  value <= stars ? Icons.star_rounded : Icons.star_outline_rounded,
                  color: value <= stars
                      ? Colors.amber
                      : Theme.of(context).colorScheme.outline,
                ),
              );
            }),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: controller,
            maxLength: _commentMaxLength,
            minLines: 3,
            maxLines: 5,
            decoration: const InputDecoration(
              labelText: 'Comentario opcional',
            ),
          ),
          if (existing != null) ...[
            const SizedBox(height: 8),
            Text(
              'Calificación registrada: ${existing.stars} de 5',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (existing.comment != null && existing.comment!.trim().isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('Comentario actual: ${existing.comment!}'),
            ],
            if (existing.ratedAt != null) ...[
              const SizedBox(height: 4),
              Text('Fecha: ${_formatDate(existing.ratedAt)}'),
            ],
          ],
          const SizedBox(height: 12),
          AppPrimaryButton(
            label: existing == null
                ? 'Enviar calificación'
                : 'Actualizar calificación',
            isLoading: isSubmitting,
            onPressed: isSubmitting
                ? null
                : () => _submitTargetRating(
                      target: target,
                      stars: stars,
                      comment: controller.text,
                      isUpdate: existing != null,
                    ),
          ),
        ],
      ),
    );
  }

  Future<void> _submitTargetRating({
    required RatingTargetModel target,
    required int stars,
    required String comment,
    required bool isUpdate,
  }) async {
    if (stars < 1 || stars > 5) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Selecciona una calificación.'),
        ),
      );
      return;
    }

    if (comment.trim().length > _commentMaxLength) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('El comentario supera el límite permitido.'),
        ),
      );
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(
          isUpdate ? '¿Actualizar calificación?' : '¿Enviar calificación?',
        ),
        content: const Text(
          'Tu opinión ayudará a mejorar la atención del taller.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(isUpdate ? 'Actualizar' : 'Enviar'),
          ),
        ],
      ),
    );

    if (confirmed != true) {
      return;
    }

    final key = _targetKey(target.targetType, target.targetId);
    setState(() => _submittingTargets.add(key));

    try {
      final response = await ref
          .read(ratingControllerProvider(widget.serviceId).notifier)
          .submitRating(
            targetType: target.targetType,
            targetId: target.targetId,
            stars: stars,
            comment: comment.trim().isEmpty ? null : comment.trim(),
          );
      if (!mounted) {
        return;
      }
      final localizedMessage = localizeBackendMessage(response.message);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            localizedMessage.isNotEmpty
                ? localizedMessage
                : 'Calificación registrada correctamente.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_mapRatingError(error))),
      );
    } finally {
      if (mounted) {
        setState(() => _submittingTargets.remove(key));
      }
    }
  }
}

class _ServiceSummaryCard extends StatelessWidget {
  const _ServiceSummaryCard({
    required this.data,
    required this.serviceSummary,
  });

  final RatingStatusModel data;
  final ClientActiveServiceModel? serviceSummary;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Servicio de auxilio',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          _InfoRow(
            label: 'Estado del servicio',
            value: localizeStatusLabel(data.serviceState),
          ),
          if (serviceSummary?.workshopName != null)
            _InfoRow(
              label: 'Taller',
              value: serviceSummary!.workshopName!,
            ),
          if (serviceSummary?.operarioName != null)
            _InfoRow(
              label: 'Operario',
              value: serviceSummary!.operarioName!,
            ),
          if (serviceSummary?.detectedSpecialty != null)
            _InfoRow(
              label: 'Especialidad',
              value: serviceSummary!.detectedSpecialty!,
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
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 4),
          Text(value),
        ],
      ),
    );
  }
}

ClientActiveServiceModel? _findServiceSummary(
  List<ClientActiveServiceModel>? items,
  int serviceId,
) {
  if (items == null) {
    return null;
  }
  for (final item in items) {
    if (item.serviceId == serviceId) {
      return item;
    }
  }
  return null;
}

ExistingRatingModel? _findExistingRating(
  List<ExistingRatingModel> items,
  String targetType,
  int? targetId,
) {
  for (final item in items) {
    if (item.targetType == targetType && item.targetId == targetId) {
      return item;
    }
  }
  return null;
}

String _targetKey(String type, int? id) => '$type:${id ?? 'null'}';

String _mapRatingError(Object error) {
  if (error is ApiException) {
    final backendDetail = _extractBackendDetail(error.details);
    final localizedDetail = localizeBackendMessage(backendDetail);
    if (localizedDetail.isNotEmpty && localizedDetail != backendDetail) {
      return localizedDetail;
    }
    if (error.statusCode == 404) {
      return 'No se encontró el servicio.';
    }
    if (error.statusCode == 409) {
      return 'El servicio no está en un estado válido para calificación.';
    }
    if (error.statusCode == 422) {
      return 'Revisa la calificación enviada.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró o no tienes permiso para esta acción.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo registrar la calificación.';
    }
  }
  return 'No se pudo conectar con el servidor.';
}

String? _extractBackendDetail(dynamic details) {
  if (details is String) {
    return details;
  }
  if (details is Map<String, dynamic>) {
    final detail = details['detail'];
    if (detail is String) {
      return detail;
    }
    if (detail is Map<String, dynamic>) {
      return _extractBackendDetail(detail);
    }
    if (detail is List && detail.isNotEmpty) {
      final first = detail.first;
      if (first is String) {
        return first;
      }
      if (first is Map<String, dynamic> && first['msg'] is String) {
        return first['msg'] as String;
      }
    }
  }
  return null;
}

String _formatDate(DateTime? value) {
  if (value == null) {
    return 'Fecha no disponible';
  }
  final localValue = value.toLocal();
  return '${localValue.day.toString().padLeft(2, '0')}/'
      '${localValue.month.toString().padLeft(2, '0')}/'
      '${localValue.year} '
      '${localValue.hour.toString().padLeft(2, '0')}:'
      '${localValue.minute.toString().padLeft(2, '0')}';
}
