import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/payment_initiation_response_model.dart';
import '../../data/models/payment_status_model.dart';
import '../../data/models/payment_summary_model.dart';
import '../../data/repositories/payments_repository.dart';

class PaymentViewModel {
  final PaymentSummaryModel summary;
  final PaymentStatusModel? latestStatus;
  final PaymentInitiationResponseModel? initiation;

  const PaymentViewModel({
    required this.summary,
    this.latestStatus,
    this.initiation,
  });
}

final paymentControllerProvider = StateNotifierProvider.family<
    PaymentController,
    AsyncValue<PaymentViewModel>,
    int>((ref, serviceId) {
  final repository = ref.watch(paymentsRepositoryProvider);
  return PaymentController(repository, serviceId);
});

class PaymentController extends StateNotifier<AsyncValue<PaymentViewModel>> {
  PaymentController(this._repository, this._serviceId)
      : super(const AsyncValue.loading()) {
    loadSummary();
  }

  final PaymentsRepository _repository;
  final int _serviceId;

  Future<void> loadSummary() async {
    state = const AsyncValue.loading();
    try {
      final summary = await _repository.getPaymentSummary(_serviceId);
      PaymentStatusModel? status;
      try {
        status = await _repository.getPaymentStatus(_serviceId);
      } catch (_) {
        status = null;
      }
      state = AsyncValue.data(
        PaymentViewModel(
          summary: summary,
          latestStatus: status,
        ),
      );
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> refreshStatus() async {
    final current = state.valueOrNull;
    if (current == null) {
      await loadSummary();
      return;
    }

    try {
      final summary = await _repository.getPaymentSummary(_serviceId);
      final status = await _repository.getPaymentStatus(_serviceId);
      state = AsyncValue.data(
        PaymentViewModel(
          summary: summary,
          latestStatus: status,
          initiation: current.initiation,
        ),
      );
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<PaymentInitiationResponseModel> initiatePayment(int methodId) async {
    final current = state.valueOrNull;
    if (current == null) {
      throw StateError('Payment summary not loaded.');
    }

    final initiation = await _repository.initiatePayment(
      serviceId: _serviceId,
      paymentMethodId: methodId,
    );

    PaymentStatusModel? refreshedStatus;
    try {
      refreshedStatus = await _repository.getPaymentStatus(_serviceId);
    } catch (_) {
      refreshedStatus = current.latestStatus;
    }

    final refreshedSummary = await _repository.getPaymentSummary(_serviceId);
    state = AsyncValue.data(
      PaymentViewModel(
        summary: refreshedSummary,
        latestStatus: refreshedStatus,
        initiation: initiation,
      ),
    );
    return initiation;
  }
}
