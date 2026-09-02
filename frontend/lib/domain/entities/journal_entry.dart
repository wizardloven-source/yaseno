// lib/domain/entities/journal_entry.dart
import 'package:decimal/decimal.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';

class JournalEntry extends Equatable {
  final String id;
  final String? number;
  final DateTime date;
  final String description;
  final String? transactionType;
  final List<JournalLine> lines;
  final bool isPosted;
  final DateTime? postedAt;
  final String? postedBy;
  final String? reversedEntryId;
  final String? reversesEntryId;
  final int version;
  final String? createdBy;
  final DateTime? createdAt;

  const JournalEntry({
    required this.id,
    this.number,
    required this.date,
    required this.description,
    this.transactionType,
    required this.lines,
    this.isPosted = false,
    this.postedAt,
    this.postedBy,
    this.reversedEntryId,
    this.reversesEntryId,
    this.version = 1,
    this.createdBy,
    this.createdAt,
  });

  Decimal get totalDebit {
    return lines.fold(Decimal.zero, (sum, line) => sum + line.debit);
  }

  Decimal get totalCredit {
    return lines.fold(Decimal.zero, (sum, line) => sum + line.credit);
  }

  bool get isBalanced => totalDebit == totalCredit;
  bool get isDraft => !isPosted && reversedEntryId == null;
  bool get isReversed => reversedEntryId != null;

  String get statusDisplay {
    if (isPosted) return 'مرحلة';
    if (isReversed) return 'معكوس';
    return 'مسودة';
  }

  Color get statusColor {
    if (isPosted) return Colors.green;
    if (isReversed) return Colors.orange;
    return Colors.blue;
  }

  IconData get statusIcon {
    if (isPosted) return Icons.check_circle;
    if (isReversed) return Icons.undo;
    return Icons.edit;
  }

  JournalEntry copyWith({
    String? id,
    String? number,
    DateTime? date,
    String? description,
    String? transactionType,
    List<JournalLine>? lines,
    bool? isPosted,
    DateTime? postedAt,
    String? postedBy,
    String? reversedEntryId,
    String? reversesEntryId,
    int? version,
  }) {
    return JournalEntry(
      id: id ?? this.id,
      number: number ?? this.number,
      date: date ?? this.date,
      description: description ?? this.description,
      transactionType: transactionType ?? this.transactionType,
      lines: lines ?? this.lines,
      isPosted: isPosted ?? this.isPosted,
      postedAt: postedAt ?? this.postedAt,
      postedBy: postedBy ?? this.postedBy,
      reversedEntryId: reversedEntryId ?? this.reversedEntryId,
      reversesEntryId: reversesEntryId ?? this.reversesEntryId,
      version: version ?? this.version,
    );
  }

  factory JournalEntry.fromJson(Map<String, dynamic> json) {
    return JournalEntry(
      id: json['id'] as String,
      number: json['number'] as String?,
      date: DateTime.parse(json['date'] as String),
      description: json['description'] as String,
      transactionType: json['transaction_type'] as String? ?? json['transactionType'] as String?,
      lines: (json['lines'] as List?)
              ?.map((e) => JournalLine.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      isPosted: json['is_posted'] as bool? ?? json['isPosted'] as bool? ?? false,
      postedAt: json['posted_at'] != null
          ? DateTime.parse(json['posted_at'] as String)
          : json['postedAt'] != null
              ? DateTime.parse(json['postedAt'] as String)
              : null,
      postedBy: json['posted_by'] as String? ?? json['postedBy'] as String?,
      reversedEntryId: json['reversed_entry_id'] as String? ?? json['reversedEntryId'] as String?,
      reversesEntryId: json['reverses_entry_id'] as String? ?? json['reversesEntryId'] as String?,
      version: json['version'] as int? ?? 1,
      createdBy: json['created_by'] as String? ?? json['createdBy'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'number': number,
      'date': date.toIso8601String(),
      'description': description,
      'transaction_type': transactionType,
      'lines': lines.map((e) => e.toJson()).toList(),
      'is_posted': isPosted,
      'posted_at': postedAt?.toIso8601String(),
      'posted_by': postedBy,
      'reversed_entry_id': reversedEntryId,
      'reverses_entry_id': reversesEntryId,
      'version': version,
      'created_by': createdBy,
    };
  }

  @override
  List<Object?> get props => [
        id,
        number,
        date,
        description,
        transactionType,
        lines,
        isPosted,
        postedAt,
        postedBy,
        reversedEntryId,
        reversesEntryId,
        version,
      ];
}

class JournalLine extends Equatable {
  final String lineId;
  final String accountCode;
  final String accountName;
  final Decimal debit;
  final Decimal credit;
  final String currency;
  final String? costCenter;
  final String? profitCenter;

  const JournalLine({
    required this.lineId,
    required this.accountCode,
    required this.accountName,
    required this.debit,
    required this.credit,
    required this.currency,
    this.costCenter,
    this.profitCenter,
  });

  bool get isDebit => debit > Decimal.zero;
  bool get isCredit => credit > Decimal.zero;
  bool get isEmpty => accountCode.isEmpty && debit == Decimal.zero && credit == Decimal.zero;

  JournalLine copyWith({
    String? lineId,
    String? accountCode,
    String? accountName,
    Decimal? debit,
    Decimal? credit,
    String? currency,
    String? costCenter,
    String? profitCenter,
  }) {
    return JournalLine(
      lineId: lineId ?? this.lineId,
      accountCode: accountCode ?? this.accountCode,
      accountName: accountName ?? this.accountName,
      debit: debit ?? this.debit,
      credit: credit ?? this.credit,
      currency: currency ?? this.currency,
      costCenter: costCenter ?? this.costCenter,
      profitCenter: profitCenter ?? this.profitCenter,
    );
  }

  factory JournalLine.fromJson(Map<String, dynamic> json) {
    return JournalLine(
      lineId: json['line_id'] as String? ?? json['lineId'] as String,
      accountCode: json['account_code'] as String? ?? json['accountCode'] as String,
      accountName: json['account_name'] as String? ?? json['accountName'] as String,
      debit: Decimal.parse(json['debit'].toString()),
      credit: Decimal.parse(json['credit'].toString()),
      currency: json['currency'] as String? ?? 'USD',
      costCenter: json['cost_center'] as String? ?? json['costCenter'] as String?,
      profitCenter: json['profit_center'] as String? ?? json['profitCenter'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'line_id': lineId,
      'account_code': accountCode,
      'account_name': accountName,
      'debit': debit.toString(),
      'credit': credit.toString(),
      'currency': currency,
      'cost_center': costCenter,
      'profit_center': profitCenter,
    };
  }

  @override
  List<Object?> get props => [
        lineId,
        accountCode,
        accountName,
        debit,
        credit,
        currency,
        costCenter,
        profitCenter,
      ];
}