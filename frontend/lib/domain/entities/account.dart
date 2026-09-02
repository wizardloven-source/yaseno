// lib/domain/entities/account.dart
import 'package:equatable/equatable.dart';
import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';

class Account extends Equatable {
  final String code;
  final String name;
  final String accountType;
  final bool isActive;
  final String currency;
  final String? parentCode;
  final String? description;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final int version;
  final List<Account>? children;
  final Decimal? balance;

  const Account({
    required this.code,
    required this.name,
    required this.accountType,
    this.isActive = true,
    this.currency = 'USD',
    this.parentCode,
    this.description,
    this.createdAt,
    this.updatedAt,
    this.version = 1,
    this.children,
    this.balance,
  });

  bool get isParent => children != null && children!.isNotEmpty;
  bool get isLeaf => children == null || children!.isEmpty;
  bool get isAsset => accountType == 'asset';
  bool get isLiability => accountType == 'liability';
  bool get isEquity => accountType == 'equity';
  bool get isRevenue => accountType == 'revenue';
  bool get isExpense => accountType == 'expense';

  String get typeDisplay {
    switch (accountType) {
      case 'asset':
        return 'أصل';
      case 'liability':
        return 'خصم';
      case 'equity':
        return 'حقوق ملكية';
      case 'revenue':
        return 'إيراد';
      case 'expense':
        return 'مصروف';
      default:
        return accountType;
    }
  }

  Color get typeColor {
    switch (accountType) {
      case 'asset':
        return Colors.blue;
      case 'liability':
        return Colors.orange;
      case 'equity':
        return Colors.purple;
      case 'revenue':
        return Colors.green;
      case 'expense':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Account copyWith({
    String? code,
    String? name,
    String? accountType,
    bool? isActive,
    String? currency,
    String? parentCode,
    String? description,
    DateTime? createdAt,
    DateTime? updatedAt,
    int? version,
    List<Account>? children,
    Decimal? balance,
  }) {
    return Account(
      code: code ?? this.code,
      name: name ?? this.name,
      accountType: accountType ?? this.accountType,
      isActive: isActive ?? this.isActive,
      currency: currency ?? this.currency,
      parentCode: parentCode ?? this.parentCode,
      description: description ?? this.description,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      version: version ?? this.version,
      children: children ?? this.children,
      balance: balance ?? this.balance,
    );
  }

  factory Account.fromJson(Map<String, dynamic> json) {
    return Account(
      code: json['code'] as String,
      name: json['name'] as String,
      accountType: json['account_type'] as String? ?? json['accountType'] as String? ?? '',
      isActive: json['is_active'] as bool? ?? json['isActive'] as bool? ?? true,
      currency: json['currency'] as String? ?? 'USD',
      parentCode: json['parent_code'] as String? ?? json['parentCode'] as String?,
      description: json['description'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : json['createdAt'] != null
              ? DateTime.parse(json['createdAt'] as String)
              : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : json['updatedAt'] != null
              ? DateTime.parse(json['updatedAt'] as String)
              : null,
      version: json['version'] as int? ?? 1,
      children: json['children'] != null
          ? (json['children'] as List)
              .map((e) => Account.fromJson(e as Map<String, dynamic>))
              .toList()
          : null,
      balance: json['balance'] != null
          ? Decimal.parse(json['balance'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'code': code,
      'name': name,
      'account_type': accountType,
      'is_active': isActive,
      'currency': currency,
      'parent_code': parentCode,
      'description': description,
      'version': version,
    };
  }

  @override
  List<Object?> get props => [
        code,
        name,
        accountType,
        isActive,
        currency,
        parentCode,
        description,
        version,
        children,
        balance,
      ];
}