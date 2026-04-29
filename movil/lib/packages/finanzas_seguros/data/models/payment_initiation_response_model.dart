import 'payment_status_model.dart';

class PaymentInitiationResponseModel {
  final PaymentInfoModel payment;

  const PaymentInitiationResponseModel({
    required this.payment,
  });

  factory PaymentInitiationResponseModel.fromJson(Map<String, dynamic> json) {
    return PaymentInitiationResponseModel(
      payment: PaymentInfoModel.fromJson(json),
    );
  }
}
