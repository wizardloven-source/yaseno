// lib/domain/entities/purchase_order.dart
import 'package:equatable/equatable.dart';
import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';

class PurchaseOrder extends Equatable {
  final String id;
  final String? number;
  final DateTime date;
  final DateTime? expectedDeliveryDate;
  final String supplierId;
  final String supplierName;
  final String? siteId;
  final String? siteName;
  final String currency;
  final String paymentTerms;
  final List<PurchaseLine> lines;
  final String status;
  final String? journalEntryId;
  final String? notes;
  final DateTime createdAt;
  final String createdBy;
  final DateTime? postedAt;
  final String? postedBy;
  final DateTime? receivedAt;
  final String? receivedBy;
  final int version;

  const PurchaseOrder({
    required this.id,
    this.number,
    required this.date,
    this.expectedDeliveryDate,
    required this.supplierId,
    required this.supplierName,
    this.siteId,
    this.siteName,
    required this.currency,
    required this.paymentTerms,
    required this.lines,
    required this.status,
    this.journalEntryId,
    this.notes,
    required this.createdAt,
    required this.createdBy,
    this.postedAt,
    this.postedBy,
    this.receivedAt,
    this.receivedBy,
    this.version = 1,
  });

  Decimal get subtotal {
    return lines.fold(Decimal.zero, (sum, line) => sum + line.total);
  }

  Decimal get total => subtotal;
  
  bool get isPosted => status == 'posted';
  bool get isDraft => status == 'draft';
  bool get isCancelled => status == 'cancelled';
  bool get isFullyReceived => status == 'fully_received';
  bool get isPartiallyReceived => status == 'partially_received';

  String get statusDisplay {
    switch (status) {
      case 'posted':
        return 'مرحلة';
      case 'cancelled':
        return 'ملغى';
      case 'fully_received':
        return 'مستلم بالكامل';
      case 'partially_received':
        return 'مستلم جزئياً';
      default:
        return 'مسودة';
    }
  }

  Color get statusColor {
    switch (status) {
      case 'posted':
        return Colors.blue;
      case 'fully_received':
        return Colors.green;
      case 'partially_received':
        return Colors.orange;
      case 'cancelled':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  PurchaseOrder copyWith({
    String? id,
    String? number,
    DateTime? date,
    DateTime? expectedDeliveryDate,
    String? supplierId,
    String? supplierName,
    String? siteId,
    String? siteName,
    String? currency,
    String? paymentTerms,
    List<PurchaseLine>? lines,
    String? status,
    String? journalEntryId,
    String? notes,
    DateTime? createdAt,
    String? createdBy,
    DateTime? postedAt,
    String? postedBy,
    DateTime? receivedAt,
    String? receivedBy,
    int? version,
  }) {
    return PurchaseOrder(
      id: id ?? this.id,
      number: number ?? this.number,
      date: date ?? this.date,
      expectedDeliveryDate: expectedDeliveryDate ?? this.expectedDeliveryDate,
      supplierId: supplierId ?? this.supplierId,
      supplierName: supplierName ?? this.supplierName,
      siteId: siteId ?? this.siteId,
      siteName: siteName ?? this.siteName,
      currency: currency ?? this.currency,
      paymentTerms: paymentTerms ?? this.paymentTerms,
      lines: lines ?? this.lines,
      status: status ?? this.status,
      journalEntryId: journalEntryId ?? this.journalEntryId,
      notes: notes ?? this.notes,
      createdAt: createdAt ?? this.createdAt,
      createdBy: createdBy ?? this.createdBy,
      postedAt: postedAt ?? this.postedAt,
      postedBy: postedBy ?? this.postedBy,
      receivedAt: receivedAt ?? this.receivedAt,
      receivedBy: receivedBy ?? this.receivedBy,
      version: version ?? this.version,
    );
  }

  factory PurchaseOrder.fromJson(Map<String, dynamic> json) {
    return PurchaseOrder(
      id: json['id'] as String? ?? '',
      number: json['number'] as String?,
      date: DateTime.parse(json['date'] as String? ?? DateTime.now().toIso8601String()),
      expectedDeliveryDate: (json['expected_delivery_date'] ?? json['expectedDeliveryDate']) != null
          ? DateTime.parse((json['expected_delivery_date'] ?? json['expectedDeliveryDate']) as String)
          : null,
      supplierId: json['supplier_id'] as String? ?? json['supplierId'] as String? ?? '',
      supplierName: json['supplier_name'] as String? ?? json['supplierName'] as String? ?? '',
      siteId: json['site_id'] as String? ?? json['siteId'] as String?,
      siteName: json['site_name'] as String? ?? json['siteName'] as String?,
      currency: json['currency'] as String? ?? 'USD',
      paymentTerms: json['payment_terms'] as String? ?? json['paymentTerms'] as String? ?? 'net_30',
      lines: (json['lines'] as List?)
              ?.map((e) => PurchaseLine.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      status: json['status'] as String? ?? 'draft',
      journalEntryId: json['journal_entry_id'] as String? ?? json['journalEntryId'] as String?,
      notes: json['notes'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String? ?? json['createdAt'] as String? ?? DateTime.now().toIso8601String()),
      createdBy: json['created_by'] as String? ?? json['createdBy'] as String? ?? 'system',
      postedAt: (json['posted_at'] ?? json['postedAt']) != null
          ? DateTime.parse((json['posted_at'] ?? json['postedAt']) as String)
          : null,
      postedBy: json['posted_by'] as String? ?? json['postedBy'] as String?,
      receivedAt: (json['received_at'] ?? json['receivedAt']) != null
          ? DateTime.parse((json['received_at'] ?? json['receivedAt']) as String)
          : null,
      receivedBy: json['received_by'] as String? ?? json['receivedBy'] as String?,
      version: json['version'] as int? ?? 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'number': number,
      'date': date.toIso8601String(),
      'expectedDeliveryDate': expectedDeliveryDate?.toIso8601String(),
      'supplierId': supplierId,
      'supplierName': supplierName,
      'siteId': siteId,
      'siteName': siteName,
      'currency': currency,
      'paymentTerms': paymentTerms,
      'lines': lines.map((e) => e.toJson()).toList(),
      'status': status,
      'journalEntryId': journalEntryId,
      'notes': notes,
      'createdAt': createdAt.toIso8601String(),
      'createdBy': createdBy,
      'postedAt': postedAt?.toIso8601String(),
      'postedBy': postedBy,
      'receivedAt': receivedAt?.toIso8601String(),
      'receivedBy': receivedBy,
      'version': version,
    };
  }

  @override
  List<Object?> get props => [
        id,
        number,
        date,
        expectedDeliveryDate,
        supplierId,
        supplierName,
        siteId,
        siteName,
        currency,
        paymentTerms,
        lines,
        status,
        journalEntryId,
        notes,
        createdAt,
        createdBy,
        postedAt,
        postedBy,
        receivedAt,
        receivedBy,
        version,
      ];
}

class PurchaseLine extends Equatable {
  final String lineId;
  final String productCode;
  final String productName;
  final Decimal quantity;
  final Decimal unitPrice;
  final Decimal total;
  final String currency;
  final String? notes;
  final Decimal receivedQuantity;
  final String? batchNumber;
  final List<String> serialNumbers;
  final DateTime? expiryDate;
  final String? location;

  const PurchaseLine({
    required this.lineId,
    required this.productCode,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    required this.total,
    required this.currency,
    this.notes,
    required this.receivedQuantity,
    this.batchNumber,
    this.serialNumbers = const [],
    this.expiryDate,
    this.location,
  });

  bool get isFullyReceived => receivedQuantity >= quantity;
  bool get hasBatch => batchNumber != null;
  bool get hasSerialNumbers => serialNumbers.isNotEmpty;

  PurchaseLine copyWith({
    String? lineId,
    String? productCode,
    String? productName,
    Decimal? quantity,
    Decimal? unitPrice,
    Decimal? total,
    String? currency,
    String? notes,
    Decimal? receivedQuantity,
    String? batchNumber,
    List<String>? serialNumbers,
    DateTime? expiryDate,
    String? location,
  }) {
    return PurchaseLine(
      lineId: lineId ?? this.lineId,
      productCode: productCode ?? this.productCode,
      productName: productName ?? this.productName,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
      total: total ?? this.total,
      currency: currency ?? this.currency,
      notes: notes ?? this.notes,
      receivedQuantity: receivedQuantity ?? this.receivedQuantity,
      batchNumber: batchNumber ?? this.batchNumber,
      serialNumbers: serialNumbers ?? this.serialNumbers,
      expiryDate: expiryDate ?? this.expiryDate,
      location: location ?? this.location,
    );
  }

  factory PurchaseLine.fromJson(Map<String, dynamic> json) {
    return PurchaseLine(
      lineId: json['line_id'] as String? ?? json['lineId'] as String? ?? '',
      productCode: json['product_code'] as String? ?? json['productCode'] as String? ?? '',
      productName: json['product_name'] as String? ?? json['productName'] as String? ?? '',
      quantity: Decimal.parse((json['quantity'] ?? 0).toString()),
      unitPrice: Decimal.parse((json['unit_price'] ?? json['unitPrice'] ?? 0).toString()),
      total: Decimal.parse((json['total'] ?? 0).toString()),
      currency: json['currency'] as String? ?? 'USD',
      notes: json['notes'] as String?,
      receivedQuantity: (json['received_quantity'] ?? json['receivedQuantity']) != null
          ? Decimal.parse((json['received_quantity'] ?? json['receivedQuantity']).toString())
          : Decimal.zero,
      batchNumber: json['batch_number'] as String? ?? json['batchNumber'] as String?,
      serialNumbers: (json['serial_numbers'] ?? json['serialNumbers'] as List?)?.cast<String>() ?? [],
      expiryDate: (json['expiry_date'] ?? json['expiryDate']) != null
          ? DateTime.parse((json['expiry_date'] ?? json['expiryDate']) as String)
          : null,
      location: json['location'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'lineId': lineId,
      'productCode': productCode,
      'productName': productName,
      'quantity': quantity.toString(),
      'unitPrice': unitPrice.toString(),
      'total': total.toString(),
      'currency': currency,
      'notes': notes,
      'receivedQuantity': receivedQuantity.toString(),
      'batchNumber': batchNumber,
      'serialNumbers': serialNumbers,
      'expiryDate': expiryDate?.toIso8601String(),
      'location': location,
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
        receivedQuantity,
        batchNumber,
        serialNumbers,
        expiryDate,
        location,
      ];
}