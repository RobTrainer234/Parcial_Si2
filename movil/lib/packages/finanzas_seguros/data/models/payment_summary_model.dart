import '../../../inteligencia_triaje/data/models/parse_helpers.dart';
import 'payment_method_model.dart';
import 'payment_status_model.dart';

class PaymentSummaryModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final double totalAmountDue;
  final double sparePartsCost;
  final double? laborCost;
  final List<PaymentMethodModel> paymentMethods;
  final bool payableNow;
  final PaymentInfoModel? existingPayment;

  const PaymentSummaryModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    required this.totalAmountDue,
    required this.sparePartsCost,
    this.laborCost,
    required this.paymentMethods,
    required this.payableNow,
    this.existingPayment,
  });

  factory PaymentSummaryModel.fromJson(Map<String, dynamic> json) {
    final rawMethods = json['payment_methods'];
    return PaymentSummaryModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      totalAmountDue: parseDoubleOrZero(json['total_amount_due']),
      sparePartsCost: parseDoubleOrZero(json['spare_parts_cost']),
      laborCost: parseNullableDouble(json['labor_cost']),
      paymentMethods: rawMethods is List
          ? rawMethods
              .whereType<Map<String, dynamic>>()
              .map(PaymentMethodModel.fromJson)
              .where((item) => item.idMetodoPago > 0)
              .toList()
          : const [],
      payableNow: json['payable_now'] as bool? ?? false,
      existingPayment: json['existing_payment'] is Map<String, dynamic>
          ? PaymentInfoModel.fromJson(
              json['existing_payment'] as Map<String, dynamic>,
            )
          : null,
    );
  }
}
