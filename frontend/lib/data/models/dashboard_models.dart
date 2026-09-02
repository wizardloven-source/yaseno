// frontend/lib/data/models/dashboard_models.dart
/// نماذج بيانات لوحة التحكم
import 'package:decimal/decimal.dart';
import '../../utils/money_utils.dart';

class MonthlyChartData {
  final int monthIndex;
  final String monthName;
  final Decimal revenue;
  final Decimal expenses;

  MonthlyChartData({
    required this.monthIndex,
    required this.monthName,
    required this.revenue,
    required this.expenses,
  });

  factory MonthlyChartData.fromJson(Map<String, dynamic> json) {
    return MonthlyChartData(
      monthIndex: json['month_index'] ?? 0,
      monthName: json['month_name'] ?? '',
      revenue: parseMoney(json['revenue']) ?? Decimal.zero,
      expenses: parseMoney(json['expenses']) ?? Decimal.zero,
    );
  }
}

class RecentEntryModel {
  final String id;
  final String? description;
  final DateTime date;
  final Decimal totalDebit;
  final bool isPosted;

  RecentEntryModel({
    required this.id,
    this.description,
    required this.date,
    required this.totalDebit,
    required this.isPosted,
  });

  factory RecentEntryModel.fromJson(Map<String, dynamic> json) {
    return RecentEntryModel(
      id: json['id'] ?? '',
      description: json['description'],
      date: DateTime.tryParse(json['date'] ?? '') ?? DateTime.now(),
      totalDebit: parseMoney(json['total_debit']) ?? Decimal.zero,
      isPosted: json['is_posted'] ?? false,
    );
  }
}

class AlertModel {
  final String id;
  final String message;
  final String severity; // critical, warning, info
  final DateTime createdAt;

  AlertModel({
    required this.id,
    required this.message,
    required this.severity,
    required this.createdAt,
  });

  factory AlertModel.fromJson(Map<String, dynamic> json) {
    return AlertModel(
      id: json['id'] ?? '',
      message: json['message'] ?? '',
      severity: json['severity'] ?? 'info',
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
    );
  }
}