// ============================================================================
// AppColors — لوحة الألوان الموحّدة للمشروع
// ============================================================================
// قاعدة الألوان 60-30-10:
//   60%  الخلفيات/السطوح المحايدة (background, surface, surfaceContainer)
//   30%  الألوان الثانوية والثلاثية والمؤكّدات (secondary, tertiary, success,
//        warning, danger)
//   10%  اللون الأساسي (primary) للإجراءات والارتباطات والتركيز
//
// الأساسي   Primary   : #164B6E (كحلي احترافي)
// الثانوي   Secondary : #1976A8
// الخلفية   Background: #F5F6FA
// النصوص    Text      : #243447
// الثانوية  Muted     : #7A8A9B
// النجاح    Success   : #1FA85B
// التحذير   Warning   : #E07B1F
// الخطر     Danger    : #D64545
// الحقول    Input     : خلفية اللون الأساسي للثيم، حدود #D3D9E0
//
// كل الألوان المشتقة (light/dark/container) مبنية على اللوحة أعلاه.
// في الوضع الداكن تُقرأ السطوح من Theme.of(context).colorScheme.
// ============================================================================

import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // ─── اللوحة الأساسية (المعايير الإلزامية) ──────────────────
  static const Color primary = Color(0xFF164B6E); // الأساسي (كحلي احترافي أعمق)
  static const Color secondary = Color(0xFF1976A8); // الثانوي
  static const Color background = Color(0xFFF5F6FA); // الخلفية
  static const Color textPrimary = Color(0xFF243447); // النصوص الأساسية
  static const Color textMuted = Color(0xFF7A8A9B); // النصوص الثانوية
  static const Color success = Color(0xFF1FA85B); // النجاح
  static const Color warning = Color(0xFFE07B1F); // التحذير
  static const Color danger = Color(0xFFD64545); // الخطر
  static const Color inputBorder = Color(0xFFD3D9E0); // حدود الحقول

  // ─── مشتقات الأساسي ────────────────────────────────────────
  static const Color primaryLight = Color(0xFF2E7FB0);
  static const Color primaryDark = Color(0xFF0E3B59);
  static const Color primaryContainer = Color(0xFFE2EDF5);
  static const Color onPrimaryContainer = Color(0xFF0B2A3F);

  // ─── مشتقات الثانوي ────────────────────────────────────────
  static const Color secondaryLight = Color(0xFF55A6CF);
  static const Color secondaryDark = Color(0xFF155E84);
  static const Color secondaryContainer = Color(0xFFDCECF5);
  static const Color onSecondaryContainer = Color(0xFF0B2A3F);
  static const Color edit = secondary; // زر التعديل

  // ─── الثلاثي (لون خامس مكمّل) ──────────────────────────────
  static const Color tertiary = Color(0xFF1ABC9C);
  static const Color tertiaryContainer = Color(0xFFD4F0EA);
  static const Color onTertiaryContainer = Color(0xFF05443A);

  // ─── السطوح/الطبقات المحايدة ───────────────────────────────
  static const Color surface = Color(0xFFF5F6FA);
  static const Color surfaceVariant = Color(0xFFF1F3F7); // صفوف الجداول المتناوبة
  static const Color surfaceContainer = Color(0xFFFFFFFF);
  static const Color surfaceContainerLow = Color(0xFFF5F6FA);
  static const Color surfaceContainerHigh = Color(0xFFE8ECF2);
  static const Color outline = Color(0xFFD3D9E0); // حدود الحقول
  static const Color outlineVariant = Color(0xFFE6EAEF);

  // ─── دلالية ────────────────────────────────────────────────
  static const Color successLight = Color(0xFF27C06A);
  static const Color successContainer = Color(0xFFE8F8EE);
  static const Color warningLight = Color(0xFFF09A3C);
  static const Color warningContainer = Color(0xFFFDF2E3);
  static const Color error = Color(0xFFD64545); // الخطر
  static const Color errorLight = Color(0xFFEB6B5F);
  static const Color errorContainer = Color(0xFFFDEAEA);
  static const Color info = Color(0xFF1976A8);
  static const Color infoContainer = Color(0xFFE3F0F8);

  // ─── القائمة الجانبية (Sidebar) ────────────────────────────
  static const Color sidebarBackground = Color(0xFFFFFFFF); // خلفية بيضاء
  static const Color sidebarSelected = Color(0xFFE2EDF5);
  static const Color sidebarHover = Color(0xFFF5F7FA);
  static const Color sidebarText = Color(0xFF2C3E50);
  static const Color sidebarTextSelected = Color(0xFF1A5276);
  static const Color sidebarIcon = Color(0xFF5D7B93);
  static const Color sidebarIconSelected = Color(0xFF1A5276);
  static const Color sidebarDivider = Color(0xFFEDF0F3);
  static const Color sidebarSectionHeader = Color(0xFF7F8C8D);

  // ─── البطاقات (Cards) ──────────────────────────────────────
  static const Color cardBackground = Color(0xFFFFFFFF); // خلفية بيضاء
  static const Color cardShadow = Color(0x0F000000); // 0 2px 12px rgba(0,0,0,0.06)
  static const Color cardBorder = Color(0xFFEDF0F3);

  // ─── النصوص ────────────────────────────────────────────────
  static const Color textSecondary = Color(0xFF7F8C8D); // Muted
  static const Color textHint = Color(0xFF95A5A6);
  static const Color textOnPrimary = Color(0xFFFFFFFF);

  // ─── الخلفيات ──────────────────────────────────────────────
  static const Color backgroundLight = Color(0xFFFFFFFF);

  // ─── ألوان أزرار الإجراءات (الموحدة) ───────────────────────
  static const Color buttonCancel = Color(0xFF95A5A6); // زر الإلغاء

  // ─── التدرّجات (Gradients) ─────────────────────────────────
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, primaryLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient headerGradient = LinearGradient(
    colors: [primaryDark, primary, primaryLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient successGradient = LinearGradient(
    colors: [success, successLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient warningGradient = LinearGradient(
    colors: [warning, warningLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // ─── ألوان بطاقات لوحة التحكم (Dashboard) ──────────────────
  static const Color dashboardBlue = Color(0xFF1A5276);
  static const Color dashboardGreen = Color(0xFF27AE60);
  static const Color dashboardOrange = Color(0xFFE67E22);
  static const Color dashboardPurple = Color(0xFF8E44AD);
  static const Color dashboardTeal = Color(0xFF16A085);
  static const Color dashboardRed = Color(0xFFE74C3C);
}
