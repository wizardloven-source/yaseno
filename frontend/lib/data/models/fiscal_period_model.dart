// frontend/lib/data/models/fiscal_period_model.dart
/// نموذج الفترة المالية

class FiscalPeriodModel {
  final String id;
  final String reference;
  final String name;
  final DateTime startDate;
  final DateTime endDate;
  final String periodType;
  final String status;
  final bool isAdjustment;
  final String? adjustmentReason;
  final String? closedBy;
  final DateTime? closedAt;
  final int version;

  FiscalPeriodModel({
    required this.id,
    required this.reference,
    required this.name,
    required this.startDate,
    required this.endDate,
    required this.periodType,
    required this.status,
    this.isAdjustment = false,
    this.adjustmentReason,
    this.closedBy,
    this.closedAt,
    this.version = 1,
  });

  factory FiscalPeriodModel.fromJson(Map<String, dynamic> json) {
    return FiscalPeriodModel(
      id: json['id'] ?? '',
      reference: json['reference'] ?? '',
      name: json['name'] ?? '',
      startDate: DateTime.tryParse(json['start_date'] ?? '') ?? DateTime.now(),
      endDate: DateTime.tryParse(json['end_date'] ?? '') ?? DateTime.now(),
      periodType: json['period_type'] ?? 'monthly',
      status: json['status'] ?? 'draft',
      isAdjustment: json['is_adjustment'] ?? false,
      adjustmentReason: json['adjustment_reason'],
      closedBy: json['closed_by'],
      closedAt: json['closed_at'] != null ? DateTime.tryParse(json['closed_at']) : null,
      version: json['version'] ?? 1,
    );
  }

  bool get isOpen => status == 'open';
  bool get isClosed => status == 'closed';

  String get statusDisplay {
    switch (status) {
      case 'open':
        return 'مفتوحة';
      case 'closed':
        return 'مغلقة';
      case 'draft':
        return 'مسودة';
      default:
        return status;
    }
  }

  String get typeDisplay {
    switch (periodType) {
      case 'monthly':
        return 'شهرية';
      case 'quarterly':
        return 'ربع سنوية';
      case 'yearly':
        return 'سنوية';
      case 'adjustment':
        return 'تعديل';
      default:
        return periodType;
    }
  }
}