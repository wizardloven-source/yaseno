// frontend/lib/data/models/accounting/account.dart

class Account {
  final String code;
  final String name;
  final String accountType;
  final bool isActive;
  final String currency;
  final String? parentCode;
  final String? description;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  Account({
    required this.code,
    required this.name,
    required this.accountType,
    required this.isActive,
    required this.currency,
    this.parentCode,
    this.description,
    this.createdAt,
    this.updatedAt,
  });

  factory Account.fromJson(Map<String, dynamic> json) {
    return Account(
      code: json['code'],
      name: json['name'],
      accountType: json['account_type'],
      isActive: json['is_active'],
      currency: json['currency'],
      parentCode: json['parent_code'],
      description: json['description'],
      createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : null,
      updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : null,
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
    };
  }
}
