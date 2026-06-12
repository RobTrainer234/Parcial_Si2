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
import '../../../gestion_auxilio/data/models/client_active_service_model.dart';
import '../../../gestion_auxilio/presentation/controllers/active_services_controller.dart';
import '../../data/models/payment_method_model.dart';
import '../../data/models/payment_status_model.dart';
import '../controllers/payment_controller.dart';

class ServicePaymentPage extends ConsumerStatefulWidget {
  const ServicePaymentPage({
    super.key,
    required this.serviceId,
  });

  final int serviceId;

  @override
  ConsumerState<ServicePaymentPage> createState() => _ServicePaymentPageState();
}

class _ServicePaymentPageState extends ConsumerState<ServicePaymentPage> {
  bool _submitting = false;

  @override
  Widget build(BuildContext context) {
    final paymentState = ref.watch(paymentControllerProvider(widget.serviceId));
    final activeServices = ref.watch(activeServicesProvider).valueOrNull;
    final serviceSummary = _findServiceSummary(activeServices, widget.serviceId);

    return AppPageScaffold(
      label: 'PAGO',
      title: 'Pago del servicio',
      subtitle: 'Confirma el pago para finalizar tu asistencia.',
      actions: IconButton(
        tooltip: 'Actualizar',
        onPressed: _submitting
            ? null
            : () => ref
                .read(paymentControllerProvider(widget.serviceId).notifier)
                .refreshStatus(),
        icon: const Icon(Icons.refresh_rounded),
      ),
      child: paymentState.when(
        loading: () => const AppLoading(message: 'Cargando pago...'),
        error: (error, _) => AppErrorView(
          message: _mapPaymentError(error),
          onRetry: () => ref
              .read(paymentControllerProvider(widget.serviceId).notifier)
              .loadSummary(),
        ),
        data: (data) {
          final summary = data.summary;
          final latestPayment =
              data.latestStatus?.payment ?? summary.existingPayment;
          final cashMethod = _findCashMethod(summary.paymentMethods);
          final isPaid = _isPaid(data);
          final canPayCash =
              summary.serviceState == 'FINALIZADO_PENDIENTE_PAGO' &&
                  summary.payableNow &&
                  cashMethod != null &&
                  !isPaid;

          return RefreshIndicator(
            onRefresh: () => ref
                .read(paymentControllerProvider(widget.serviceId).notifier)
                .refreshStatus(),
            child: ListView(
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _InfoRow(
                        label: 'Servicio',
                        value: 'Servicio de auxilio',
                      ),
                      if (serviceSummary?.workshopName != null)
                        _InfoRow(
                          label: 'Taller',
                          value: serviceSummary!.workshopName!,
                        ),
                      _InfoRow(
                        label: 'Monto',
                        value:
                            'BOB ${summary.totalAmountDue.toStringAsFixed(2)}',
                      ),
                      const _InfoRow(
                        label: 'Moneda',
                        value: 'BOB',
                      ),
                      _InfoRow(
                        label: 'Estado del pago',
                        value: latestPayment == null
                            ? 'Pendiente'
                            : localizeStatusLabel(latestPayment.paymentStatus),
                      ),
                      _InfoRow(
                        label: 'Estado del servicio',
                        value: localizeStatusLabel(summary.serviceState),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                if (isPaid)
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Servicio pagado',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        const Text('Este servicio ya fue pagado.'),
                        if (latestPayment != null) ...[
                          const SizedBox(height: 12),
                          _PaymentInfoBlock(payment: latestPayment),
                        ],
                        const SizedBox(height: 16),
                        AppPrimaryButton(
                          label: 'Calificar servicio',
                          onPressed: () => context.push(
                            AppRoutes.serviceRatingPath(widget.serviceId),
                          ),
                        ),
                      ],
                    ),
                  )
                else
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Método de pago',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        if (cashMethod == null)
                          const Text(
                            'No hay un método de pago en efectivo disponible.',
                          )
                        else
                          _CashMethodCard(method: cashMethod),
                        if (latestPayment != null) ...[
                          const SizedBox(height: 16),
                          _PaymentInfoBlock(payment: latestPayment),
                        ],
                        const SizedBox(height: 16),
                        if (!summary.payableNow &&
                            summary.serviceState != 'PAGADO')
                          const Text(
                            'El servicio aún no está listo para pago.',
                          ),
                        const SizedBox(height: 16),
                        AppPrimaryButton(
                          label: 'Confirmar pago en efectivo',
                          isLoading: _submitting,
                          onPressed: canPayCash ? _confirmCashPayment : null,
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton(
                      onPressed: _submitting
                          ? null
                          : () => ref
                              .read(paymentControllerProvider(widget.serviceId)
                                  .notifier)
                              .refreshStatus(),
                      child: const Text('Actualizar'),
                    ),
                    OutlinedButton(
                      onPressed: () => context.go(
                        AppRoutes.serviceTrackingPath(widget.serviceId),
                      ),
                      child: const Text('Volver al seguimiento'),
                    ),
                    OutlinedButton(
                      onPressed: () => context.go(AppRoutes.clientHome),
                      child: const Text('Volver al inicio'),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  bool _isPaid(PaymentViewModel data) {
    if (data.latestStatus?.serviceState == 'PAGADO') {
      return true;
    }
    return data.latestStatus?.payment?.paymentStatus == 'CONFIRMADO' ||
        data.summary.existingPayment?.paymentStatus == 'CONFIRMADO';
  }

  Future<void> _confirmCashPayment() async {
    final state = ref.read(paymentControllerProvider(widget.serviceId)).valueOrNull;
    final cashMethod =
        state == null ? null : _findCashMethod(state.summary.paymentMethods);
    if (cashMethod == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No hay un método de pago en efectivo disponible.'),
        ),
      );
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('¿Confirmar pago en efectivo?'),
        content: const Text(
          'Al confirmar, el servicio quedará pagado y podrás calificar la atención.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Confirmar pago'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() => _submitting = true);
    try {
      final response = await ref
          .read(paymentControllerProvider(widget.serviceId).notifier)
          .initiatePayment(cashMethod.idMetodoPago);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            localizeBackendMessage(response.payment.message).isNotEmpty
                ? localizeBackendMessage(response.payment.message)
                : 'Pago registrado correctamente.',
          ),
        ),
      );
      context.go(AppRoutes.serviceTrackingPath(widget.serviceId));
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_mapPaymentError(error))),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

class _CashMethodCard extends StatelessWidget {
  const _CashMethodCard({
    required this.method,
  });

  final PaymentMethodModel method;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.colorScheme.outline),
      ),
      child: Row(
        children: [
          Icon(
            Icons.payments_outlined,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Pagar en efectivo'),
                SizedBox(height: 4),
                Text('Registra el pago presencial del servicio.'),
              ],
            ),
          ),
          if (!method.activo)
            Text(
              'Inactivo',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.error,
              ),
            ),
        ],
      ),
    );
  }
}

class _PaymentInfoBlock extends StatelessWidget {
  const _PaymentInfoBlock({
    required this.payment,
  });

  final PaymentInfoModel payment;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _InfoRow(
          label: 'Estado del pago',
          value: localizeStatusLabel(payment.paymentStatus),
        ),
        _InfoRow(
          label: 'Monto',
          value: 'BOB ${payment.amount.toStringAsFixed(2)}',
        ),
        _InfoRow(
          label: 'Método',
          value: payment.method,
        ),
        if (payment.confirmedAt != null)
          _InfoRow(
            label: 'Confirmado',
            value: _formatDate(payment.confirmedAt),
          ),
        if (payment.message != null && payment.message!.trim().isNotEmpty)
          _InfoRow(
            label: 'Detalle',
            value: localizeBackendMessage(payment.message!),
          ),
      ],
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

PaymentMethodModel? _findCashMethod(List<PaymentMethodModel> methods) {
  for (final method in methods) {
    if (method.activo && method.nombre.trim().toUpperCase() == 'EFECTIVO') {
      return method;
    }
  }
  return null;
}

String _mapPaymentError(Object error) {
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
      return 'El servicio no está en un estado válido para pago.';
    }
    if (error.statusCode == 422) {
      return 'Revisa los datos enviados.';
    }
    if (error.statusCode == 401 || error.statusCode == 403) {
      return 'Tu sesión expiró o no tienes permiso para esta acción.';
    }
    if (error.statusCode != null && error.statusCode! >= 500) {
      return 'No se pudo registrar el pago.';
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
