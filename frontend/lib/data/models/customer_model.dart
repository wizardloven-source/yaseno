import 'package:decimal/decimal.dart';
import '../../utils/money_utils.dart';

class Customer {
  final String id;
  final String code;
  final String name;
  final String? email;
  final String? phone;
  final String? mobile;
  final String? street;
  final String? city;
  final String country;
  final String? taxNumber;
  final Decimal creditLimit;
  final String currency;
  final String? notes;
  final String status;
  final bool isDeleted;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int version;

  Customer({
    required this.id,
    required this.code,
    required this.name,
    this.email,
    this.phone,
    this.mobile,
    this.street,
    this.city,
    this.country = 'LB',
    this.taxNumber,
    Decimal? creditLimit,
    this.currency = 'USD',
    this.notes,
    required this.status,
    this.isDeleted = false,
    required this.createdAt,
    required this.updatedAt,
    required this.version,
  }) : creditLimit = creditLimit ?? Decimal.zero;

  factory Customer.fromJson(Map<String, dynamic> json) {
    return Customer(
      id: json['id'] ?? '',
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      email: json['email'],
      phone: json['phone'],
      mobile: json['mobile'],
      street: json['street'],
      city: json['city'],
      country: json['country'] ?? 'LB',
      taxNumber: json['tax_number'] as String? ?? json['taxNumber'] as String?,
      creditLimit: parseMoney(json['credit_limit'] ?? json['creditLimit']) ?? Decimal.zero,
      currency: json['currency'] ?? 'USD',
      notes: json['notes'],
      status: json['status'] ?? 'active',
      isDeleted: json['is_deleted'] as bool? ?? json['isDeleted'] as bool? ?? false,
      createdAt: DateTime.parse(json['created_at'] as String? ?? json['createdAt'] as String? ?? DateTime.now().toIso8601String()),
      updatedAt: DateTime.parse(json['updated_at'] as String? ?? json['updatedAt'] as String? ?? DateTime.now().toIso8601String()),
      version: json['version'] ?? 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'code': code,
      'name': name,
      'email': email,
      'phone': phone,
      'mobile': mobile,
      'street': street,
      'city': city,
      'country': country,
      'taxNumber': taxNumber,
      'creditLimit': creditLimit.toString(),
      'currency': currency,
      'notes': notes,
      'status': status,
    };
  }

  Map<String, dynamic> toUpdateJson() {
    return {
      'name': name,
      'email': email,
      'phone': phone,
      'mobile': mobile,
      'street': street,
      'city': city,
      'country': country,
      'taxNumber': taxNumber,
      'creditLimit': creditLimit.toString(),
      'currency': currency,
      'notes': notes,
      'version': version,
    };
  }
}