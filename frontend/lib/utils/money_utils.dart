// frontend/lib/utils/money_utils.dart
// أدوات موحدة للتعامل مع المال في الواجهة.
//
// الهدف: تمثيل المبالغ النقدية دائماً بـ [Decimal] (بدقة عشرية كاملة)
// بدلاً من double الذي يفقد الدقة في العمليات الحسابية.
library;

import 'package:decimal/decimal.dart';

/// تحويل أي قيمة نقدية (num, String, Decimal) إلى [Decimal].
///
/// - `num` → يحوَّل عبر نصه لالتقاط التمثيل العشري النظيف.
/// - `String` → يُحذف منه فواصل الآلاف ويُحلَّل.
/// - يُرجع `null` عند غياب القيمة أو عدم صلاحيتها.
Decimal? parseMoney(dynamic value) {
  if (value == null) return null;
  if (value is Decimal) return value;
  if (value is int) return Decimal.fromInt(value);
  if (value is num) return Decimal.parse(value.toString());
  if (value is String) {
    final s = value.trim().replaceAll(',', '');
    if (s.isEmpty) return null;
    return Decimal.tryParse(s);
  }
  return null;
}

/// مثل [parseMoney] لكن يعيد `Decimal.zero` عند الغياب/الخطأ.
Decimal parseMoneyOrZero(dynamic value) => parseMoney(value) ?? Decimal.zero;

/// تنسيق مبلغ مع فواصل الآلاف وعدد ثابت من المنازل العشرية (افتراضي 2).
String formatMoney(dynamic value, {int? decimals, bool grouping = true}) {
  final d = parseMoney(value);
  if (d == null) return '0';
  final dec = decimals ?? 2;
  final fixed = d.toStringAsFixed(dec);
  if (!grouping) return fixed;
  final negative = fixed.startsWith('-');
  final unsigned = negative ? fixed.substring(1) : fixed;
  final parts = unsigned.split('.');
  final intPart = parts[0];
  final fracPart = parts.length > 1 ? parts[1] : '';
  final buffer = StringBuffer();
  for (var i = 0; i < intPart.length; i++) {
    if (i > 0 && (intPart.length - i) % 3 == 0) buffer.write(',');
    buffer.write(intPart[i]);
  }
  final signed = buffer.toString();
  return '${negative ? '-' : ''}$signed${fracPart.isEmpty ? '' : '.$fracPart'}';
}

/// تنسيق مبلغ مع عملة (رمز العملة يظهر كعنوان لاحق مثل `100.00 USD`).
String formatMoneyCurrency(dynamic value, {String? currency, int? decimals}) {
  final c = (currency ?? '').trim().toUpperCase();
  final dec = decimals ?? currencyDecimals(c);
  final s = formatMoney(value, decimals: dec);
  return c.isEmpty ? s : '$s $c';
}

/// عدد المنازل العشرية المعتاد لعملة معينة.
int currencyDecimals(String? currency) {
  switch ((currency ?? '').trim().toUpperCase()) {
    case 'IQD':
    case 'JOD':
    case 'OMR':
    case 'BHD':
    case 'KWD':
    case 'TND':
    case 'LYD':
      return 3;
    case 'JPY':
    case 'KRW':
    case 'CLP':
    case 'ISK':
      return 0;
    default:
      return 2;
  }
}

/// مجموع قائمة من القيم النقدية (أي نوع) بدقة [Decimal].
Decimal moneySum(Iterable<dynamic> values) => values.fold(
    Decimal.zero, (a, b) => a + (parseMoney(b) ?? Decimal.zero));