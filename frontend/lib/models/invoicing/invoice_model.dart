// lib/models/invoice_model.dart
import 'package:decimal/decimal.dart';
import '../../utils/money_utils.dart';

class InvoiceModel {
  final String id;
  final String? number;
  final DateTime date;
  final String customerId;
  final String customerName;
  final String? siteId;
  final String? siteName;
  final String currency;
  final String paymentCurrency;
  final String paymentType;
  final String? fundId;
  final String status;
  final Decimal subtotal;
  final Decimal taxAmount;
  final Decimal total;
  final Decimal? totalWithTax;
  final bool isTaxInclusive;
  final Map<String, Decimal> taxBreakdown;
  final List<String> taxRatesApplied;
  final String? notes;
  final String? journalEntryId;
  final DateTime? postedAt;
  final String? postedBy;
  final DateTime createdAt;
  final String createdBy;
  final List<InvoiceLineModel> lines;

  InvoiceModel({
    required this.id,
    this.number,
    required this.date,
    required this.customerId,
    required this.customerName,
    this.siteId,
    this.siteName,
    required this.currency,
    required this.paymentCurrency,
    required this.paymentType,
    this.fundId,
    required this.status,
    required this.subtotal,
    required this.taxAmount,
    required this.total,
    this.totalWithTax,
    this.isTaxInclusive = false,
    this.taxBreakdown = const {},
    this.taxRatesApplied = const [],
    this.notes,
    this.journalEntryId,
    this.postedAt,
    this.postedBy,
    required this.createdAt,
    required this.createdBy,
    this.lines = const [],
  });

  factory InvoiceModel.fromJson(Map<String, dynamic> json) {
    return InvoiceModel(
      id: json['id'] ?? '',
      number: json['number'],
      date: DateTime.parse(json['date']),
      customerId: json['customer_id'] ?? '',
      customerName: json['customer_name'] ?? '',
      siteId: json['site_id'],
      siteName: json['site_name'],
      currency: json['currency'] ?? 'USD',
      paymentCurrency: json['payment_currency'] ?? 'USD',
      paymentType: json['payment_type'] ?? 'cash',
      fundId: json['fund_id'],
      status: json['status'] ?? 'draft',
      subtotal: parseMoney(json['subtotal']) ?? Decimal.zero,
      taxAmount: parseMoney(json['tax_amount']) ?? Decimal.zero,
      total: parseMoney(json['total']) ?? Decimal.zero,
      totalWithTax: parseMoney(json['total_with_tax']),
      isTaxInclusive: json['is_tax_inclusive'] ?? false,
      taxBreakdown: (json['tax_breakdown'] as Map<String, dynamic>? ?? {})
          .map((k, v) => MapEntry(k, parseMoney(v) ?? Decimal.zero)),
      taxRatesApplied: List<String>.from(json['tax_rates_applied'] ?? []),
      notes: json['notes'],
      journalEntryId: json['journal_entry_id'],
      postedAt: json['posted_at'] != null ? DateTime.parse(json['posted_at']) : null,
      postedBy: json['posted_by'],
      createdAt: DateTime.parse(json['created_at']),
      createdBy: json['created_by'] ?? 'system',
      lines: (json['lines'] as List? ?? [])
          .map((l) => InvoiceLineModel.fromJson(l))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'number': number,
      'date': date.toIso8601String(),
      'customer_id': customerId,
      'customer_name': customerName,
      'site_id': siteId,
      'site_name': siteName,
      'currency': currency,
      'payment_currency': paymentCurrency,
      'payment_type': paymentType,
      'fund_id': fundId,
      'status': status,
      'subtotal': subtotal.toString(),
      'tax_amount': taxAmount.toString(),
      'total': total.toString(),
      'total_with_tax': totalWithTax?.toString(),
      'is_tax_inclusive': isTaxInclusive,
      'tax_breakdown': taxBreakdown.map((k, v) => MapEntry(k, v.toString())),
      'tax_rates_applied': taxRatesApplied,
      'notes': notes,
      'journal_entry_id': journalEntryId,
      'posted_at': postedAt?.toIso8601String(),
      'posted_by': postedBy,
      'created_at': createdAt.toIso8601String(),
      'created_by': createdBy,
      'lines': lines.map((l) => l.toJson()).toList(),
    };
  }

  InvoiceModel copyWith({
    String? id,
    String? number,
    DateTime? date,
    String? customerId,
    String? customerName,
    String? siteId,
    String? siteName,
    String? currency,
    String? paymentCurrency,
    String? paymentType,
    String? fundId,
    String? status,
    Decimal? subtotal,
    Decimal? taxAmount,
    Decimal? total,
    Decimal? totalWithTax,
    bool? isTaxInclusive,
    Map<String, Decimal>? taxBreakdown,
    List<String>? taxRatesApplied,
    String? notes,
    String? journalEntryId,
    DateTime? postedAt,
    String? postedBy,
    DateTime? createdAt,
    String? createdBy,
    List<InvoiceLineModel>? lines,
  }) {
    return InvoiceModel(
      id: id ?? this.id,
      number: number ?? this.number,
      date: date ?? this.date,
      customerId: customerId ?? this.customerId,
      customerName: customerName ?? this.customerName,
      siteId: siteId ?? this.siteId,
      siteName: siteName ?? this.siteName,
      currency: currency ?? this.currency,
      paymentCurrency: paymentCurrency ?? this.paymentCurrency,
      paymentType: paymentType ?? this.paymentType,
      fundId: fundId ?? this.fundId,
      status: status ?? this.status,
      subtotal: subtotal ?? this.subtotal,
      taxAmount: taxAmount ?? this.taxAmount,
      total: total ?? this.total,
      totalWithTax: totalWithTax ?? this.totalWithTax,
      isTaxInclusive: isTaxInclusive ?? this.isTaxInclusive,
      taxBreakdown: taxBreakdown ?? this.taxBreakdown,
      taxRatesApplied: taxRatesApplied ?? this.taxRatesApplied,
      notes: notes ?? this.notes,
      journalEntryId: journalEntryId ?? this.journalEntryId,
      postedAt: postedAt ?? this.postedAt,
      postedBy: postedBy ?? this.postedBy,
      createdAt: createdAt ?? this.createdAt,
      createdBy: createdBy ?? this.createdBy,
      lines: lines ?? this.lines,
    );
  }

  bool get isPosted => status == 'posted';
  bool get isDraft => status == 'draft';
  bool get isCancelled => status == 'cancelled';
  String get statusDisplay {
    switch (status) {
      case 'draft': return 'مسودة';
      case 'posted': return 'مرحلة';
      case 'cancelled': return 'ملغاة';
      default: return status;
    }
  }
}

class InvoiceLineModel {
  final String lineId;
  final String productCode;
  final String productName;
  final Decimal quantity;
  final Decimal unitPrice;
  final Decimal total;
  final String currency;
  final String? notes;
  final Decimal? taxRate;
  final Decimal? taxAmount;
  final bool? isTaxInclusive;

  InvoiceLineModel({
    required this.lineId,
    required this.productCode,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    required this.total,
    required this.currency,
    this.notes,
    this.taxRate,
    this.taxAmount,
    this.isTaxInclusive,
  });

  factory InvoiceLineModel.fromJson(Map<String, dynamic> json) {
    return InvoiceLineModel(
      lineId: json['line_id'] ?? '',
      productCode: json['product_code'] ?? '',
      productName: json['product_name'] ?? '',
      quantity: parseMoney(json['quantity']) ?? Decimal.zero,
      unitPrice: parseMoney(json['unit_price']) ?? Decimal.zero,
      total: parseMoney(json['total']) ?? Decimal.zero,
      currency: json['currency'] ?? 'USD',
      notes: json['notes'],
      taxRate: parseMoney(json['tax_rate']),
      taxAmount: parseMoney(json['tax_amount']),
      isTaxInclusive: json['is_tax_inclusive'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'line_id': lineId,
      'product_code': productCode,
      'product_name': productName,
      'quantity': quantity.toString(),
      'unit_price': unitPrice.toString(),
      'total': total.toString(),
      'currency': currency,
      'notes': notes,
      'tax_rate': taxRate?.toString(),
      'tax_amount': taxAmount?.toString(),
      'is_tax_inclusive': isTaxInclusive,
    };
  }
}