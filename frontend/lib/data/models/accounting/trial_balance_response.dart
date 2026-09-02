// c:\Users\MTC\Desktop\yaseeno\frontend\lib\data\models\accounting\trial_balance_response.dart

// c:\Users\MTC\Desktop\yaseeno\frontend\lib\data\models\accounting\trial_balance_response.dart
import 'package:decimal/decimal.dart';
import '../../../utils/money_utils.dart';

class TrialBalanceResponse {
  final bool success;
  final TrialBalanceData? data;
  final String? message;
  final List<String>? errors;

  TrialBalanceResponse({
    required this.success,
    this.data,
    this.message,
    this.errors,
  });

  factory TrialBalanceResponse.fromJson(Map<String, dynamic> json) {
    return TrialBalanceResponse(
      success: json['success'] as bool,
      data: json['data'] != null ? TrialBalanceData.fromJson(json['data']) : null,
      message: json['message'] as String?,
      errors: (json['errors'] as List<dynamic>?)?.map((e) => e as String).toList(),
    );
  }
}

class TrialBalanceData {
  final String asOf;
  final String currency;
  final bool isBalanced;
  final Decimal totalDebits;
  final Decimal totalCredits;
  final Decimal difference;
  final List<TrialBalanceAccount> accounts;

  TrialBalanceData({
    required this.asOf,
    required this.currency,
    required this.isBalanced,
    required this.totalDebits,
    required this.totalCredits,
    required this.difference,
    required this.accounts,
  });

  factory TrialBalanceData.fromJson(Map<String, dynamic> json) {
    return TrialBalanceData(
      asOf: json['as_of'] as String,
      currency: json['currency'] as String,
      isBalanced: json['is_balanced'] as bool,
      totalDebits: parseMoney(json['total_debits']) ?? Decimal.zero,
      totalCredits: parseMoney(json['total_credits']) ?? Decimal.zero,
      difference: parseMoney(json['difference']) ?? Decimal.zero,
      accounts: (json['accounts'] as List<dynamic>)
          .map((e) => TrialBalanceAccount.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class TrialBalanceAccount {
  final String accountCode;
  final Decimal balance;
  final String currency;

  TrialBalanceAccount({
    required this.accountCode,
    required this.balance,
    required this.currency,
  });

  factory TrialBalanceAccount.fromJson(Map<String, dynamic> json) {
    return TrialBalanceAccount(
      accountCode: json['account_code'] as String,
      balance: parseMoney(json['balance']) ?? Decimal.zero,
      currency: json['currency'] as String,
    );
  }
}
