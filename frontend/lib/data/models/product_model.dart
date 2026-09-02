import 'package:decimal/decimal.dart';
import '../../utils/money_utils.dart';

class Product {
  final String id;
  final String code;
  final String name;
  final String? description;
  final String? category;
  final Decimal unitPrice;
  final String currency;
  final Decimal taxRate;
  final int stockQuantity;
  final bool isActive;
  final bool isDeleted;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int version;

  Product({
    required this.id,
    required this.code,
    required this.name,
    this.description,
    this.category,
    required this.unitPrice,
    this.currency = 'USD',
    Decimal? taxRate,
    this.stockQuantity = 0,
    this.isActive = true,
    this.isDeleted = false,
    required this.createdAt,
    required this.updatedAt,
    required this.version,
  }) : taxRate = taxRate ?? Decimal.zero;

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] ?? '',
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      description: json['description'],
      category: json['category'],
      unitPrice: parseMoney(json['unit_price'] ?? json['unitPrice']) ?? Decimal.zero,
      currency: json['currency'] ?? 'USD',
      taxRate: parseMoney(json['tax_rate'] ?? json['taxRate']) ?? Decimal.zero,
      stockQuantity: json['stock_quantity'] as int? ?? json['stockQuantity'] as int? ?? 0,
      isActive: json['is_active'] as bool? ?? json['isActive'] as bool? ?? true,
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
      'description': description,
      'category': category,
      'unitPrice': unitPrice.toString(),
      'currency': currency,
      'taxRate': taxRate.toString(),
      'stockQuantity': stockQuantity,
      'isActive': isActive,
    };
  }

  Map<String, dynamic> toUpdateJson() {
    return {
      'code': code,
      'name': name,
      'unitPrice': unitPrice.toString(),
      'currency': currency,
      'description': description,
      'category': category,
      'taxRate': taxRate.toString(),
      'stockQuantity': stockQuantity,
      'isActive': isActive,
      'version': version,
    };
  }

  bool get isLowStock => stockQuantity <= 10 && stockQuantity > 0;
  bool get isOutOfStock => stockQuantity <= 0;
}