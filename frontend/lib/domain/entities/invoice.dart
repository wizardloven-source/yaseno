// lib/domain/entities/invoice.dart
import 'package:equatable/equatable.dart';
import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';

class Invoice extends Equatable {
  final String id;
  final String? number;
  final DateTime date;
  final String customerId;
  final String customerName;
  final String? customerBranchId;
  final String? customerBranchName;
  final String? customerBranchCode;
  final String? siteId;
  final String? siteName;
  final String currency;
  final String paymentCurrency;
  final String paymentType;
  final String? fundId;
  final List<InvoiceLine> lines;
  final Decimal subtotal;
  final Decimal taxAmount;
  final Map<String, Decimal> taxBreakdown;
  final List<String> taxRatesApplied;
  final bool isTaxInclusive;
  final Decimal total;
  final Decimal totalWithTax;
  final String status;
  final String? journalEntryId;
  final String? notes;
  final DateTime createdAt;
  final String createdBy;
  final DateTime? postedAt;
  final String? postedBy;
  final int version;

  const Invoice({
    required this.id,
    this.number,
    required this.date,
    required this.customerId,
    required this.customerName,
    this.customerBranchId,
    this.customerBranchName,
    this.customerBranchCode,
    this.siteId,
    this.siteName,
    required this.currency,
    required this.paymentCurrency,
    required this.paymentType,
    this.fundId,
    required this.lines,
    required this.subtotal,
    required this.taxAmount,
    this.taxBreakdown = const {},
    this.taxRatesApplied = const [],
    this.isTaxInclusive = false,
    required this.total,
    required this.totalWithTax,
    required this.status,
    this.journalEntryId,
    this.notes,
    required this.createdAt,
    required this.createdBy,
    this.postedAt,
    this.postedBy,
    this.version = 1,
  });

  bool get isPosted => status == 'posted';
  bool get isDraft => status == 'draft';
  bool get isCancelled => status == 'cancelled';
  bool get hasTax => taxAmount > Decimal.zero;
  bool get hasCustomerBranch => customerBranchId != null;

  String get statusDisplay {
    switch (status) {
      case 'posted':
        return 'مرحلة';
      case 'cancelled':
        return 'ملغاة';
      default:
        return 'مسودة';
    }
  }

  Color get statusColor {
    switch (status) {
      case 'posted':
        return Colors.green;
      case 'cancelled':
        return Colors.red;
      default:
        return Colors.blue;
    }
  }

  Invoice copyWith({
    String? id,
    String? number,
    DateTime? date,
    String? customerId,
    String? customerName,
    String? customerBranchId,
    String? customerBranchName,
    String? customerBranchCode,
    String? siteId,
    String? siteName,
    String? currency,
    String? paymentCurrency,
    String? paymentType,
    String? fundId,
    List<InvoiceLine>? lines,
    Decimal? subtotal,
    Decimal? taxAmount,
    Map<String, Decimal>? taxBreakdown,
    List<String>? taxRatesApplied,
    bool? isTaxInclusive,
    Decimal? total,
    Decimal? totalWithTax,
    String? status,
    String? journalEntryId,
    String? notes,
    DateTime? createdAt,
    String? createdBy,
    DateTime? postedAt,
    String? postedBy,
    int? version,
  }) {
    return Invoice(
      id: id ?? this.id,
      number: number ?? this.number,
      date: date ?? this.date,
      customerId: customerId ?? this.customerId,
      customerName: customerName ?? this.customerName,
      customerBranchId: customerBranchId ?? this.customerBranchId,
      customerBranchName: customerBranchName ?? this.customerBranchName,
      customerBranchCode: customerBranchCode ?? this.customerBranchCode,
      siteId: siteId ?? this.siteId,
      siteName: siteName ?? this.siteName,
      currency: currency ?? this.currency,
      paymentCurrency: paymentCurrency ?? this.paymentCurrency,
      paymentType: paymentType ?? this.paymentType,
      fundId: fundId ?? this.fundId,
      lines: lines ?? this.lines,
      subtotal: subtotal ?? this.subtotal,
      taxAmount: taxAmount ?? this.taxAmount,
      taxBreakdown: taxBreakdown ?? this.taxBreakdown,
      taxRatesApplied: taxRatesApplied ?? this.taxRatesApplied,
      isTaxInclusive: isTaxInclusive ?? this.isTaxInclusive,
      total: total ?? this.total,
      totalWithTax: totalWithTax ?? this.totalWithTax,
      status: status ?? this.status,
      journalEntryId: journalEntryId ?? this.journalEntryId,
      notes: notes ?? this.notes,
      createdAt: createdAt ?? this.createdAt,
      createdBy: createdBy ?? this.createdBy,
      postedAt: postedAt ?? this.postedAt,
      postedBy: postedBy ?? this.postedBy,
      version: version ?? this.version,
    );
  }

  factory Invoice.fromJson(Map<String, dynamic> json) {
    return Invoice(
      id: json['id'] as String,
      number: json['number'] as String?,
      date: DateTime.parse(json['date'] as String),
      customerId: json['customer_id'] as String? ?? json['customerId'] as String,
      customerName: json['customer_name'] as String? ?? json['customerName'] as String,
      customerBranchId: json['customer_branch_id'] as String? ?? json['customerBranchId'] as String?,
      customerBranchName: json['customer_branch_name'] as String? ?? json['customerBranchName'] as String?,
      customerBranchCode: json['customer_branch_code'] as String? ?? json['customerBranchCode'] as String?,
      siteId: json['site_id'] as String? ?? json['siteId'] as String?,
      siteName: json['site_name'] as String? ?? json['siteName'] as String?,
      currency: json['currency'] as String? ?? 'USD',
      paymentCurrency: json['payment_currency'] as String? ?? json['paymentCurrency'] as String? ?? 'USD',
      paymentType: json['payment_type'] as String? ?? json['paymentType'] as String? ?? 'cash',
      fundId: json['fund_id'] as String? ?? json['fundId'] as String?,
      lines: (json['lines'] as List?)
              ?.map((e) => InvoiceLine.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      subtotal: Decimal.parse(json['subtotal'].toString()),
      taxAmount: Decimal.parse(json['tax_amount'] as String? ?? json['taxAmount'].toString()),
      taxBreakdown: (json['tax_breakdown'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, Decimal.parse(v.toString())),
          ) ??
          (json['taxBreakdown'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, Decimal.parse(v.toString())),
          ) ??
          {},
      taxRatesApplied: (json['tax_rates_applied'] as List?)?.cast<String>() ??
          (json['taxRatesApplied'] as List?)?.cast<String>() ??
          [],
      isTaxInclusive: json['is_tax_inclusive'] as bool? ?? json['isTaxInclusive'] as bool? ?? false,
      total: Decimal.parse(json['total'].toString()),
      totalWithTax: Decimal.parse(json['total_with_tax'] as String? ?? json['totalWithTax'].toString()),
      status: json['status'] as String? ?? 'draft',
      journalEntryId: json['journal_entry_id'] as String? ?? json['journalEntryId'] as String?,
      notes: json['notes'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String? ?? json['createdAt'] as String),
      createdBy: json['created_by'] as String? ?? json['createdBy'] as String? ?? 'system',
      postedAt: json['posted_at'] != null
          ? DateTime.parse(json['posted_at'] as String)
          : json['postedAt'] != null
              ? DateTime.parse(json['postedAt'] as String)
              : null,
      postedBy: json['posted_by'] as String? ?? json['postedBy'] as String?,
      version: json['version'] as int? ?? 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'number': number,
      'date': date.toIso8601String(),
      'customer_id': customerId,
      'customer_name': customerName,
      'customer_branch_id': customerBranchId,
      'customer_branch_name': customerBranchName,
      'customer_branch_code': customerBranchCode,
      'site_id': siteId,
      'site_name': siteName,
      'currency': currency,
      'payment_currency': paymentCurrency,
      'payment_type': paymentType,
      'fund_id': fundId,
      'lines': lines.map((e) => e.toJson()).toList(),
      'subtotal': subtotal.toString(),
      'tax_amount': taxAmount.toString(),
      'tax_breakdown': taxBreakdown.map((k, v) => MapEntry(k, v.toString())),
      'tax_rates_applied': taxRatesApplied,
      'is_tax_inclusive': isTaxInclusive,
      'total': total.toString(),
      'total_with_tax': totalWithTax.toString(),
      'status': status,
      'journal_entry_id': journalEntryId,
      'notes': notes,
      'created_at': createdAt.toIso8601String(),
      'created_by': createdBy,
      'posted_at': postedAt?.toIso8601String(),
      'posted_by': postedBy,
      'version': version,
    };
  }

  @override
  List<Object?> get props => [
        id,
        number,
        date,
        customerId,
        customerName,
        customerBranchId,
        customerBranchName,
        customerBranchCode,
        siteId,
        siteName,
        currency,
        paymentCurrency,
        paymentType,
        fundId,
        lines,
        subtotal,
        taxAmount,
        taxBreakdown,
        taxRatesApplied,
        isTaxInclusive,
        total,
        totalWithTax,
        status,
        journalEntryId,
        notes,
        createdAt,
        createdBy,
        postedAt,
        postedBy,
        version,
      ];
}

class InvoiceLine extends Equatable {
  final String lineId;
  final String productCode;
  final String productName;
  final Decimal quantity;
  final Decimal unitPrice;
  final Decimal total;
  final String currency;
  final String? notes;
  final Decimal taxRate;
  final Decimal taxAmount;
  final Map<String, Decimal> taxBreakdown;
  final bool isTaxInclusive;
  final Decimal totalWithTax;

  const InvoiceLine({
    required this.lineId,
    required this.productCode,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    required this.total,
    required this.currency,
    this.notes,
    required this.taxRate,
    required this.taxAmount,
    this.taxBreakdown = const {},
    this.isTaxInclusive = false,
    required this.totalWithTax,
  });

  bool get hasTax => taxAmount > Decimal.zero;

  InvoiceLine copyWith({
    String? lineId,
    String? productCode,
    String? productName,
    Decimal? quantity,
    Decimal? unitPrice,
    Decimal? total,
    String? currency,
    String? notes,
    Decimal? taxRate,
    Decimal? taxAmount,
    Map<String, Decimal>? taxBreakdown,
    bool? isTaxInclusive,
    Decimal? totalWithTax,
  }) {
    return InvoiceLine(
      lineId: lineId ?? this.lineId,
      productCode: productCode ?? this.productCode,
      productName: productName ?? this.productName,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
      total: total ?? this.total,
      currency: currency ?? this.currency,
      notes: notes ?? this.notes,
      taxRate: taxRate ?? this.taxRate,
      taxAmount: taxAmount ?? this.taxAmount,
      taxBreakdown: taxBreakdown ?? this.taxBreakdown,
      isTaxInclusive: isTaxInclusive ?? this.isTaxInclusive,
      totalWithTax: totalWithTax ?? this.totalWithTax,
    );
  }

  factory InvoiceLine.fromJson(Map<String, dynamic> json) {
    return InvoiceLine(
      lineId: json['line_id'] as String? ?? json['lineId'] as String,
      productCode: json['product_code'] as String? ?? json['productCode'] as String,
      productName: json['product_name'] as String? ?? json['productName'] as String,
      quantity: Decimal.parse(json['quantity'].toString()),
      unitPrice: Decimal.parse(json['unit_price'] as String? ?? json['unitPrice'].toString()),
      total: Decimal.parse(json['total'].toString()),
      currency: json['currency'] as String? ?? 'USD',
      notes: json['notes'] as String?,
      taxRate: json['tax_rate'] != null
          ? Decimal.parse(json['tax_rate'].toString())
          : json['taxRate'] != null
              ? Decimal.parse(json['taxRate'].toString())
              : Decimal.zero,
      taxAmount: json['tax_amount'] != null
          ? Decimal.parse(json['tax_amount'].toString())
          : json['taxAmount'] != null
              ? Decimal.parse(json['taxAmount'].toString())
              : Decimal.zero,
      taxBreakdown: (json['tax_breakdown'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, Decimal.parse(v.toString())),
          ) ??
          (json['taxBreakdown'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, Decimal.parse(v.toString())),
          ) ??
          {},
      isTaxInclusive: json['is_tax_inclusive'] as bool? ?? json['isTaxInclusive'] as bool? ?? false,
      totalWithTax: json['total_with_tax'] != null
          ? Decimal.parse(json['total_with_tax'].toString())
          : json['totalWithTax'] != null
              ? Decimal.parse(json['totalWithTax'].toString())
              : Decimal.zero,
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
      'tax_rate': taxRate.toString(),
      'tax_amount': taxAmount.toString(),
      'tax_breakdown': taxBreakdown.map((k, v) => MapEntry(k, v.toString())),
      'is_tax_inclusive': isTaxInclusive,
      'total_with_tax': totalWithTax.toString(),
    };
  }

  @override
  List<Object?> get props => [
        lineId,
        productCode,
        productName,
        quantity,
        unitPrice,
        total,
        currency,
        notes,
        taxRate,
        taxAmount,
        taxBreakdown,
        isTaxInclusive,
        totalWithTax,
      ];
}