// lib/domain/entities/fund.dart
import 'package:equatable/equatable.dart';
import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';

class Fund extends Equatable {
  final String id;
  final String code;
  final String name;
  final String fundType;
  final String accountCode;
  final String currency;
  final Decimal balance;
  final Decimal dailyLimit;
  final Decimal monthlyLimit;
  final Decimal minBalanceAlert;
  final Decimal maxBalanceAlert;
  final bool requiresApproval;
  final Decimal approvalThreshold;
  final String status;
  final bool isActive;
  final DateTime createdAt;
  final String createdBy;
  final DateTime updatedAt;
  final String updatedBy;
  final int version;
  final List<FundMovement>? movements;

  const Fund({
    required this.id,
    required this.code,
    required this.name,
    required this.fundType,
    required this.accountCode,
    required this.currency,
    required this.balance,
    required this.dailyLimit,
    required this.monthlyLimit,
    required this.minBalanceAlert,
    required this.maxBalanceAlert,
    required this.requiresApproval,
    required this.approvalThreshold,
    required this.status,
    required this.isActive,
    required this.createdAt,
    required this.createdBy,
    required this.updatedAt,
    required this.updatedBy,
    required this.version,
    this.movements,
  });

  bool get isLowBalance => balance <= minBalanceAlert && minBalanceAlert > Decimal.zero;
  bool get isHighBalance => balance >= maxBalanceAlert && maxBalanceAlert > Decimal.zero;
  bool get isOverDailyLimit => balance > dailyLimit && dailyLimit > Decimal.zero;
  
  String get statusDisplay {
    switch (status) {
      case 'active':
        return 'نشط';
      case 'suspended':
        return 'معلق';
      case 'closed':
        return 'مغلق';
      default:
        return status;
    }
  }

  Color get statusColor {
    switch (status) {
      case 'active':
        return Colors.green;
      case 'suspended':
        return Colors.orange;
      case 'closed':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Fund copyWith({
    String? id,
    String? code,
    String? name,
    String? fundType,
    String? accountCode,
    String? currency,
    Decimal? balance,
    Decimal? dailyLimit,
    Decimal? monthlyLimit,
    Decimal? minBalanceAlert,
    Decimal? maxBalanceAlert,
    bool? requiresApproval,
    Decimal? approvalThreshold,
    String? status,
    bool? isActive,
    DateTime? createdAt,
    String? createdBy,
    DateTime? updatedAt,
    String? updatedBy,
    int? version,
    List<FundMovement>? movements,
  }) {
    return Fund(
      id: id ?? this.id,
      code: code ?? this.code,
      name: name ?? this.name,
      fundType: fundType ?? this.fundType,
      accountCode: accountCode ?? this.accountCode,
      currency: currency ?? this.currency,
      balance: balance ?? this.balance,
      dailyLimit: dailyLimit ?? this.dailyLimit,
      monthlyLimit: monthlyLimit ?? this.monthlyLimit,
      minBalanceAlert: minBalanceAlert ?? this.minBalanceAlert,
      maxBalanceAlert: maxBalanceAlert ?? this.maxBalanceAlert,
      requiresApproval: requiresApproval ?? this.requiresApproval,
      approvalThreshold: approvalThreshold ?? this.approvalThreshold,
      status: status ?? this.status,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
      createdBy: createdBy ?? this.createdBy,
      updatedAt: updatedAt ?? this.updatedAt,
      updatedBy: updatedBy ?? this.updatedBy,
      version: version ?? this.version,
      movements: movements ?? this.movements,
    );
  }

  factory Fund.fromJson(Map<String, dynamic> json) {
    return Fund(
      id: json['id'] as String? ?? json['id'] ?? '',
      code: json['code'] as String? ?? json['code'] ?? '',
      name: json['name'] as String? ?? json['name'] ?? '',
      fundType: json['fund_type'] as String? ?? json['fundType'] as String? ?? 'main',
      accountCode: json['account_code'] as String? ?? json['accountCode'] as String? ?? '',
      currency: json['currency'] as String? ?? 'USD',
      balance: Decimal.parse((json['balance'] ?? 0).toString()),
      dailyLimit: Decimal.parse((json['daily_limit'] ?? json['dailyLimit'] ?? 0).toString()),
      monthlyLimit: Decimal.parse((json['monthly_limit'] ?? json['monthlyLimit'] ?? 0).toString()),
      minBalanceAlert: Decimal.parse((json['min_balance_alert'] ?? json['minBalanceAlert'] ?? 0).toString()),
      maxBalanceAlert: Decimal.parse((json['max_balance_alert'] ?? json['maxBalanceAlert'] ?? 0).toString()),
      requiresApproval: json['requires_approval'] as bool? ?? json['requiresApproval'] as bool? ?? false,
      approvalThreshold: Decimal.parse((json['approval_threshold'] ?? json['approvalThreshold'] ?? 0).toString()),
      status: json['status'] as String? ?? 'active',
      isActive: json['is_active'] as bool? ?? json['isActive'] as bool? ?? true,
      createdAt: DateTime.parse(json['created_at'] as String? ?? json['createdAt'] as String? ?? DateTime.now().toIso8601String()),
      createdBy: json['created_by'] as String? ?? json['createdBy'] as String? ?? 'system',
      updatedAt: DateTime.parse(json['updated_at'] as String? ?? json['updatedAt'] as String? ?? DateTime.now().toIso8601String()),
      updatedBy: json['updated_by'] as String? ?? json['updatedBy'] as String? ?? 'system',
      version: json['version'] as int? ?? 1,
      movements: json['movements'] != null
          ? (json['movements'] as List)
              .map((e) => FundMovement.fromJson(e as Map<String, dynamic>))
              .toList()
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'code': code,
      'name': name,
      'fundType': fundType,
      'accountCode': accountCode,
      'currency': currency,
      'balance': balance.toString(),
      'dailyLimit': dailyLimit.toString(),
      'monthlyLimit': monthlyLimit.toString(),
      'minBalanceAlert': minBalanceAlert.toString(),
      'maxBalanceAlert': maxBalanceAlert.toString(),
      'requiresApproval': requiresApproval,
      'approvalThreshold': approvalThreshold.toString(),
      'status': status,
      'isActive': isActive,
      'createdAt': createdAt.toIso8601String(),
      'createdBy': createdBy,
      'updatedAt': updatedAt.toIso8601String(),
      'updatedBy': updatedBy,
      'version': version,
    };
  }

  @override
  List<Object?> get props => [
        id,
        code,
        name,
        fundType,
        accountCode,
        currency,
        balance,
        dailyLimit,
        monthlyLimit,
        minBalanceAlert,
        maxBalanceAlert,
        requiresApproval,
        approvalThreshold,
        status,
        isActive,
        createdAt,
        createdBy,
        updatedAt,
        updatedBy,
        version,
        movements,
      ];
}

class FundMovement extends Equatable {
  final String id;
  final String fundId;
  final String movementType;
  final Decimal amount;
  final String currency;
  final Decimal balanceAfter;
  final String reason;
  final DateTime createdAt;
  final String createdBy;
  final String? referenceId;
  final Decimal? exchangeRateUsed;

  const FundMovement({
    required this.id,
    required this.fundId,
    required this.movementType,
    required this.amount,
    required this.currency,
    required this.balanceAfter,
    required this.reason,
    required this.createdAt,
    required this.createdBy,
    this.referenceId,
    this.exchangeRateUsed,
  });

  bool get isDeposit => movementType == 'deposit';
  bool get isWithdraw => movementType == 'withdraw';
  bool get isTransfer => movementType == 'transfer_in' || movementType == 'transfer_out';

  String get typeDisplay {
    switch (movementType) {
      case 'deposit':
        return 'إيداع';
      case 'withdraw':
        return 'سحب';
      case 'transfer_in':
        return 'تحويل وارد';
      case 'transfer_out':
        return 'تحويل صادر';
      case 'opening_balance':
        return 'رصيد افتتاحي';
      case 'adjustment':
        return 'تسوية';
      default:
        return movementType;
    }
  }

  Color get typeColor {
    if (movementType == 'deposit' || movementType == 'transfer_in' || movementType == 'opening_balance') {
      return Colors.green;
    } else if (movementType == 'withdraw' || movementType == 'transfer_out') {
      return Colors.red;
    } else {
      return Colors.orange;
    }
  }

  factory FundMovement.fromJson(Map<String, dynamic> json) {
    return FundMovement(
      id: json['id'] as String? ?? '',
      fundId: json['fund_id'] as String? ?? json['fundId'] as String? ?? '',
      movementType: json['movement_type'] as String? ?? json['movementType'] as String? ?? '',
      amount: Decimal.parse((json['amount'] ?? 0).toString()),
      currency: json['currency'] as String? ?? 'USD',
      balanceAfter: Decimal.parse((json['balance_after'] ?? json['balanceAfter'] ?? 0).toString()),
      reason: json['reason'] as String? ?? '',
      createdAt: DateTime.parse(json['created_at'] as String? ?? json['createdAt'] as String? ?? DateTime.now().toIso8601String()),
      createdBy: json['created_by'] as String? ?? json['createdBy'] as String? ?? 'system',
      referenceId: json['reference_id'] as String? ?? json['referenceId'] as String?,
      exchangeRateUsed: (json['exchange_rate_used'] ?? json['exchangeRateUsed']) != null
          ? Decimal.parse((json['exchange_rate_used'] ?? json['exchangeRateUsed']).toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'fundId': fundId,
      'movementType': movementType,
      'amount': amount.toString(),
      'currency': currency,
      'balanceAfter': balanceAfter.toString(),
      'reason': reason,
      'createdAt': createdAt.toIso8601String(),
      'createdBy': createdBy,
      'referenceId': referenceId,
      'exchangeRateUsed': exchangeRateUsed?.toString(),
    };
  }

  @override
  List<Object?> get props => [
        id,
        fundId,
        movementType,
        amount,
        currency,
        balanceAfter,
        reason,
        createdAt,
        createdBy,
        referenceId,
        exchangeRateUsed,
      ];
}