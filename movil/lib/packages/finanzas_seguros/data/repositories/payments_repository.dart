import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../models/payment_initiation_response_model.dart';
import '../models/payment_status_model.dart';
import '../models/payment_summary_model.dart';

final paymentsRepositoryProvider = Provider<PaymentsRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return PaymentsRepository(apiClient);
});

class PaymentsRepository {
  PaymentsRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<PaymentSummaryModel> getPaymentSummary(int serviceId) async {
    final response =
        await _apiClient.get('/finance/services/$serviceId/payment-summary');
    return PaymentSummaryModel.fromJson(response as Map<String, dynamic>);
  }

  Future<PaymentInitiationResponseModel> initiatePayment({
    required int serviceId,
    required int paymentMethodId,
  }) async {
    final response = await _apiClient.post(
      '/finance/services/$serviceId/payments/initiate',
      data: {'id_metodo_pago': paymentMethodId},
    );
    return PaymentInitiationResponseModel.fromJson(
      response as Map<String, dynamic>,
    );
  }

  Future<PaymentStatusModel> getPaymentStatus(int serviceId) async {
    final response =
        await _apiClient.get('/finance/services/$serviceId/payments/status');
    return PaymentStatusModel.fromJson(response as Map<String, dynamic>);
  }
}
