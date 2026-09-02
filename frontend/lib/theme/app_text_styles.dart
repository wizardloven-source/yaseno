import 'package:flutter/material.dart';
import 'app_colors.dart';

/// ألوان الوضع الداكن
class DarkText {
  DarkText._();
  static const Color text = Color(0xFFFFFFFF);
  static const Color textLight = Color(0xFFB0B8C4);
  static const Color hint = Color(0xFF6B7280);
  static const Color primary = Color(0xFF5BA8F5);
  static const Color success = Color(0xFF34D399);
  static const Color warning = Color(0xFFFBBF24);
  static const Color danger = Color(0xFFF87171);
}

class AppTextStyles {
  AppTextStyles._();

  static const String _fontFamily = 'Cairo';

  // ─── Display ────────────────────────────────────────────────
  static const TextStyle displayLarge = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 32,
    fontWeight: FontWeight.w700,
    height: 1.2,
    color: AppColors.textPrimary,
  );

  static const TextStyle displayMedium = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 28,
    fontWeight: FontWeight.w700,
    height: 1.25,
    color: AppColors.textPrimary,
  );

  static const TextStyle displaySmall = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 24,
    fontWeight: FontWeight.w700,
    height: 1.3,
    color: AppColors.textPrimary,
  );

  // ─── H2 عنوان قسم (20px SemiBold) ───────────────────────────
  static const TextStyle headlineLarge = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 20,
    fontWeight: FontWeight.w600,
    height: 1.3,
    color: AppColors.textPrimary,
  );

  static const TextStyle headlineMedium = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 20,
    fontWeight: FontWeight.w600,
    height: 1.35,
    color: AppColors.textPrimary,
  );

  static const TextStyle headlineSmall = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 18,
    fontWeight: FontWeight.w600,
    height: 1.4,
    color: AppColors.textPrimary,
  );

  // ─── Title ──────────────────────────────────────────────────
  static const TextStyle titleLarge = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 18,
    fontWeight: FontWeight.w600,
    height: 1.4,
    color: AppColors.textPrimary,
  );

  static const TextStyle titleMedium = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    height: 1.5,
    color: AppColors.textPrimary,
  );

  static const TextStyle titleSmall = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.5,
    color: AppColors.textPrimary,
  );

  // ─── Body (P, TD, LI: 16px Regular) ─────────────────────────
  static const TextStyle bodyLarge = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 1.5,
    color: AppColors.textPrimary,
  );

  static const TextStyle bodyMedium = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.5,
    color: AppColors.textPrimary,
  );

  // ─── نص مساعد (مثل التواريخ: 13px Light) ───────────────────
  static const TextStyle bodySmall = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 13,
    fontWeight: FontWeight.w300,
    height: 1.5,
    color: AppColors.textSecondary,
  );

  // ─── Label ──────────────────────────────────────────────────
  static const TextStyle labelLarge = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 14,
    fontWeight: FontWeight.w600,
    height: 1.4,
    color: AppColors.textPrimary,
  );

  static const TextStyle labelMedium = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 12,
    fontWeight: FontWeight.w600,
    height: 1.4,
    color: AppColors.textSecondary,
  );

  static const TextStyle labelSmall = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 11,
    fontWeight: FontWeight.w600,
    height: 1.4,
    color: AppColors.textSecondary,
  );

  // ─── Stat/Card Specific ─────────────────────────────────────
  static const TextStyle statValue = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 22,
    fontWeight: FontWeight.w700,
    height: 1.2,
    color: AppColors.primary,
  );

  static const TextStyle statLabel = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 12,
    fontWeight: FontWeight.w500,
    height: 1.3,
    color: AppColors.textSecondary,
  );

  // ─── Price/Money (22px Bold بلون الأساسي) ───────────────────
  static const TextStyle moneyLarge = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 22,
    fontWeight: FontWeight.w700,
    height: 1.2,
    color: AppColors.primary,
  );

  static const TextStyle moneyMedium = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    height: 1.3,
    color: AppColors.textPrimary,
  );

  // ─── Chip/Badge ────────────────────────────────────────────
  static const TextStyle chip = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 12,
    fontWeight: FontWeight.w600,
    height: 1.3,
  );

  // ─── Navigation ─────────────────────────────────────────────
  static const TextStyle navItem = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 13,
    fontWeight: FontWeight.w500,
    height: 1.4,
  );

  static const TextStyle navItemSelected = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 13,
    fontWeight: FontWeight.w600,
    height: 1.4,
  );

  static const TextStyle sectionHeader = TextStyle(
    fontFamily: _fontFamily,
    fontSize: 11,
    fontWeight: FontWeight.w600,
    height: 1.4,
    letterSpacing: 0.5,
  );

  // ═══════════════════════════════════════════════════════════════
  // أدوات مساعدة للوضع الداكن — تُرجع ألوان بيضاء/ملونة على خلفية سوداء
  // ═══════════════════════════════════════════════════════════════
  static bool _isDark(BuildContext context) => Theme.of(context).brightness == Brightness.dark;

  static TextStyle bodyLargeFor(BuildContext context) =>
      bodyLarge.copyWith(color: _isDark(context) ? DarkText.text : AppColors.textPrimary);

  static TextStyle bodyMediumFor(BuildContext context) =>
      bodyMedium.copyWith(color: _isDark(context) ? DarkText.text : AppColors.textPrimary);

  static TextStyle bodySmallFor(BuildContext context) =>
      bodySmall.copyWith(color: _isDark(context) ? DarkText.textLight : AppColors.textSecondary);

  static TextStyle titleLargeFor(BuildContext context) =>
      titleLarge.copyWith(color: _isDark(context) ? DarkText.text : AppColors.textPrimary);

  static TextStyle titleMediumFor(BuildContext context) =>
      titleMedium.copyWith(color: _isDark(context) ? DarkText.text : AppColors.textPrimary);

  static TextStyle labelLargeFor(BuildContext context) =>
      labelLarge.copyWith(color: _isDark(context) ? DarkText.text : AppColors.textPrimary);

  static TextStyle labelMediumFor(BuildContext context) =>
      labelMedium.copyWith(color: _isDark(context) ? DarkText.textLight : AppColors.textSecondary);

  static TextStyle statValueFor(BuildContext context) =>
      statValue.copyWith(color: _isDark(context) ? DarkText.primary : AppColors.primary);

  static TextStyle statLabelFor(BuildContext context) =>
      statLabel.copyWith(color: _isDark(context) ? DarkText.textLight : AppColors.textSecondary);

  static TextStyle moneyLargeFor(BuildContext context) =>
      moneyLarge.copyWith(color: _isDark(context) ? DarkText.primary : AppColors.primary);
}
