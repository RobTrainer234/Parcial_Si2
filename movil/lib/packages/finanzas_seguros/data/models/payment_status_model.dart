import '../../../inteligencia_triaje/data/models/parse_helpers.dart';

class PaymentInfoModel {
  final int paymentId;
  final String paymentStatus;
  final double amount;
  final String method;
  final String? qrPayload;
  final String? qrUrl;
  final String? paymentUrl;
  final DateTime? expiresAt;
  final String? providerReference;
  final String? message;
  final DateTime? requestedAt;
  final DateTime? confirmedAt;
  final DateTime? lastUpdate;
  final String? receipt;

  const PaymentInfoModel({
    required this.paymentId,
    required this.paymentStatus,
    required this.amount,
    required this.method,
    this.qrPayload,
    this.qrUrl,
    this.paymentUrl,
    this.expiresAt,
    this.providerReference,
    this.message,
    this.requestedAt,
    this.confirmedAt,
    this.lastUpdate,
    this.receipt,
  });

  factory PaymentInfoModel.fromJson(Map<String, dynamic> json) {
    return PaymentInfoModel(
      paymentId: parseRequiredInt(json['payment_id'], field: 'payment_id'),
      paymentStatus: json['payment_status'] as String? ?? '',
      amount: parseDoubleOrZero(json['amount']),
      method: json['method'] as String? ?? '',
      qrPayload: json['qr_payload'] as String?,
      qrUrl: json['qr_url'] as String?,
      paymentUrl: json['payment_url'] as String?,
      expiresAt: parseDate(json['expires_at']),
      providerReference: json['provider_reference'] as String?,
      message: json['message'] as String?,
      requestedAt: parseDate(json['requested_at']),
      confirmedAt: parseDate(json['confirmed_at']),
      lastUpdate: parseDate(json['last_update']),
      receipt: json['receipt'] as String?,
    );
  }
}

class PaymentStatusModel {
  final int serviceId;
  final String serviceState;
  final int incidentId;
  final PaymentInfoModel? payment;
  final bool payableNow;

  const PaymentStatusModel({
    required this.serviceId,
    required this.serviceState,
    required this.incidentId,
    this.payment,
    required this.payableNow,
  });

  factory PaymentStatusModel.fromJson(Map<String, dynamic> json) {
    return PaymentStatusModel(
      serviceId: parseRequiredInt(json['service_id'], field: 'service_id'),
      serviceState: json['service_state'] as String? ?? '',
      incidentId: parseRequiredInt(json['incident_id'], field: 'incident_id'),
      payment: json['payment'] is Map<String, dynamic>
          ? PaymentInfoModel.fromJson(json['payment'] as Map<String, dynamic>)
          : null,
      payableNow: json['payable_now'] as bool? ?? false,
    );
  }
}
