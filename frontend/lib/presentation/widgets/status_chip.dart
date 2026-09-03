import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

/// الحالات الموحّدة حسب نظام الحالات في مواصفات التصميم (§59).
enum AppStatus {
  draft('draft', 'مسودة', AppColors.textSecondary),
  submitted('submitted', 'مقدّم', AppColors.warningLight),
  pending('pending', 'قيد الانتظار', AppColors.warningLight),
  approved('approved', 'معتمد', AppColors.success),
  confirmed('confirmed', 'مؤكّد', AppColors.success),
  posted('posted', 'مرحّل', AppColors.primaryLight),
  completed('completed', 'مكتمل', AppColors.success),
  cancelled('cancelled', 'ملغي', AppColors.textMuted),
  rejected('rejected', 'مرفوض', AppColors.error),
  returned('returned', 'مُرجع', AppColors.secondary),
  reversed('reversed', 'معكوس', AppColors.textMuted),
  failed('failed', 'فشل', AppColors.error);

  const AppStatus(this.code, this.arabicLabel, this.color);

  /// الكود المستخدم في قاعدة البيانات/الـ API.
  final String code;

  /// العنوان المعروض بالعربية.
  final String arabicLabel;

  /// لون الحالة.
  final Color color;
}

/// StatusChip — شارة حالة موحّدة بقيم/ألوان متسقة عبر النظام (§58.3، §59).
///
/// يقرأ الحالة من كود الخادم (draft/pending/posted/cancelled/...) ويعرض
/// التسمية العربية واللون الموحّد. لا يعتمد على اللون وحده، لذا يُلحَق
/// رمزٌ لتوضيح الحالة (§73).
class StatusChip extends StatelessWidget {
  final String status;
  final double height;

  const StatusChip({
    super.key,
    required this.status,
    this.height = 24,
  });

  /// يطابق نص الحالة مع [AppStatus] ويُرجِع التوافق، أو حالة افتراضية.
  static AppStatus _match(String status) {
    final normalized = status.trim().toLowerCase();
    for (final s in AppStatus.values) {
      if (s.code == normalized) return s;
    }
    return AppStatus.pending;
  }

  static IconData _iconFor(AppStatus s) {
    switch (s) {
      case AppStatus.draft:
        return Icons.edit_outlined;
      case AppStatus.posted:
      case AppStatus.completed:
      case AppStatus.approved:
      case AppStatus.confirmed:
        return Icons.check_circle_outline;
      case AppStatus.cancelled:
      case AppStatus.rejected:
      case AppStatus.failed:
        return Icons.cancel_outlined;
      case AppStatus.returned:
      case AppStatus.reversed:
        return Icons.undo;
      case AppStatus.submitted:
      case AppStatus.pending:
        return Icons.schedule;
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = _match(status);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final Color chipColor = isDark ? s.color : s.color;
    final Color textColor = chipColor;
    final Color bg = chipColor.withValues(alpha: 0.12);

    return Container(
      height: height,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(height / 2),
        border: Border.all(color: chipColor.withValues(alpha: 0.4), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_iconFor(s), size: 12, color: textColor),
          const SizedBox(width: 4),
          Text(
            s.arabicLabel,
            style: AppTextStyles.labelSmall.copyWith(
              color: textColor,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
