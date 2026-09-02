// ============================================================================
// AppDimensions — نظام الأبعاد الموحّد (مضاعفات الرقم 8)
// ============================================================================
// المعايير الإلزامية:
//   - الارتفاعات: الحقول 44، الصفوف 48، الشريط العلوي 64، القائمة الجانبية 250.
//   - الهوامش الداخلية (padding): 8، 16، 24، 32، 48.
//   - المسافات (gap): 8، 16، 24.
//   - الزوايا: 8 للكروت، 6 للحقول، 4 للأزرار الصغيرة.
// ============================================================================

import 'package:flutter/material.dart';

class AppDimens {
  AppDimens._();

  // ─── الارتفاعات القياسية ───────────────────────────────────
  static const double inputHeight = 44; // الحقول
  static const double rowHeight = 48; // الصفوف
  static const double navbarHeight = 64; // الشريط العلوي
  static const double sidebarWidth = 250; // القائمة الجانبية

  // ─── الفراغات والهوامش (مضاعفات 8) ─────────────────────────
  static const double s2 = 8;
  static const double s3 = 16;
  static const double s4 = 24;
  static const double s5 = 32;
  static const double s6 = 48;
  static const double s1 = 4;

  // ─── الزوايا المدوّرة ──────────────────────────────────────
  static const double radiusCard = 8; // الكروت
  static const double radiusInput = 6; // الحقول
  static const double radiusButtonSmall = 4; // الأزرار الصغيرة

  // ─── ظل البطاقات (0 2px 12px rgba(0,0,0,0.06)) ─────────────
  static const List<BoxShadow> cardShadow = [
    BoxShadow(
      color: Color(0x0F000000),
      blurRadius: 12,
      offset: Offset(0, 2),
    ),
  ];

  // ─── طريقة هامش المحتوى حسب عرض الشاشة (تجاوب) ─────────────
  //   كبيرة (>1200) : 24
  //   متوسطة (768–1200): 16
  //   صغيرة (<768) : 12
  static double contentPaddingByWidth(double width) {
    if (width > 1200) return 24;
    if (width >= 768) return 16;
    return 12;
  }
}
