// ============================================================================
// AppWidgets — مكونات واجهة موحّدة (بطاقات، أزرار، حقول) مبنية على المعايير
// ============================================================================
// طبّق المعايير الإلزامية للتصميم:
//   - الأزرار: الإضافة/الحفظ أخضر (#27AE60)، التعديل أزرق (#2E86C1)،
//     الحذف أحمر (#E74C3C)، الإلغاء رمادي (#95A5A6). الارتفاع 44،
//     هوامش 16/24، زوايا 6، نص أبيض.
//   - البطاقات: خلفية بيضاء، ظل 0 2px 12px rgba(0,0,0,0.06)، زوايا 8.
//   - الحقول: خلفية بيضاء، حد #D5D8DC، زوايا 6، ارتفاع 44.
// ============================================================================

import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimensions.dart';

/// أزرار موحّدة بدلالة اللون حسب الإجراء.
class AppButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  /// add/save → أخضر، edit → أزرق، delete → أحمر، cancel → رمادي، default → أساسي
  final AppButtonVariant variant;
  final bool loading;
  final bool expanded;

  const AppButton({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.variant = AppButtonVariant.primary,
    this.loading = false,
    this.expanded = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = variant.backgroundColor;
    final Widget child = loading
        ? const SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: Colors.white,
            ),
          )
        : Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 20),
                const SizedBox(width: 8),
              ],
              Text(label),
            ],
          );

    final style = ElevatedButton.styleFrom(
      backgroundColor: color,
      foregroundColor: Colors.white,
      minimumSize: Size(expanded ? double.infinity : 0, AppDimens.inputHeight),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppDimens.radiusInput),
      ),
      elevation: 0,
      shadowColor: Colors.transparent,
      disabledBackgroundColor: color.withValues(alpha: 0.5),
    );

    final button = ElevatedButton(
      onPressed: loading ? null : onPressed,
      style: style,
      child: child,
    );

    return expanded ? SizedBox(width: double.infinity, child: button) : button;
  }
}

/// دلالات ألوان الأزرار الموحّدة.
enum AppButtonVariant {
  /// أخضر — إضافة/حفظ
  success(AppColors.success),

  /// أزرق — تعديل
  edit(AppColors.edit),

  /// أحمر — حذف
  danger(AppColors.danger),

  /// رمادي — إلغاء
  cancel(AppColors.buttonCancel),

  /// أساسي
  primary(AppColors.primary),

  /// ثانوي
  secondary(AppColors.secondary);

  final Color backgroundColor;
  const AppButtonVariant(this.backgroundColor);
}

/// بطاقة موحّدة: خلفية بيضاء، ظل ناعم، زوايا 8، هامش داخلي 24.
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final bool withShadow;

  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppDimens.s4),
    this.withShadow = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        border: Border.all(color: AppColors.cardBorder, width: 1),
        boxShadow: withShadow ? AppDimens.cardShadow : null,
      ),
      padding: padding,
      child: child,
    );
  }
}

/// عنوان بطاقة موحّد: 18px SemiBold بلون الأساسي.
class AppCardTitle extends StatelessWidget {
  final String title;
  final Widget? trailing;

  const AppCardTitle({super.key, required this.title, this.trailing});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.primary,
            ),
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}
