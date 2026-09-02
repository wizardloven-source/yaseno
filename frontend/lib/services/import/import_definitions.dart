// lib/services/import/import_definitions.dart
// تعريفات حقول الاستيراد لكل كيان: الأسماء العربية/الإنجليزية للأعمدة،
// والمفاتيح الخلفية (snake_case)، وأدوات التحقق والتحويل.
//
// تُستخدم هذه التعريفات من قبل محرك الاستيراد لتحديد الأعمدة تلقائياً
// حتى لو اختلفت تسميات الرؤوس في ملف الإكسل (عربي/إنجليزي/أخرى).

import '../../utils/currency_helper.dart';

/// نوع البيانات الذي سيتم استيراده.
enum ImportEntityType { customers, products, invoices }

extension ImportEntityTypeX on ImportEntityType {
  String get title {
    switch (this) {
      case ImportEntityType.customers:
        return 'استيراد العملاء';
      case ImportEntityType.products:
        return 'استيراد المنتجات';
      case ImportEntityType.invoices:
        return 'استيراد الفواتير';
    }
  }

  String get singular {
    switch (this) {
      case ImportEntityType.customers:
        return 'عميل';
      case ImportEntityType.products:
        return 'منتج';
      case ImportEntityType.invoices:
        return 'فاتورة';
    }
  }

  String get apiEndpoint {
    switch (this) {
      case ImportEntityType.customers:
        return 'customers';
      case ImportEntityType.products:
        return 'products';
      case ImportEntityType.invoices:
        return 'invoices';
    }
  }
}

/// تعريف حقل قابل للاستيراد.
class ImportField {
  /// اسم الحقل الفريد (عربي/إنجليزي داخلياً).
  final String key;

  /// المفتاح المرسل إلى الخادم (snake_case).
  final String apiKey;

  /// التسمية المعروضة في الواجهة.
  final String label;

  /// مقاومة الرؤوس المحتملة للأعمدة (عربي/إنجليزي/اختلافات).
  final List<String> aliases;

  /// هل الحقل إلزامي؟
  final bool required;

  final ImportFieldType type;

  const ImportField({
    required this.key,
    required this.apiKey,
    required this.label,
    required this.aliases,
    this.required = false,
    this.type = ImportFieldType.text,
  });
}

enum ImportFieldType { text, number, code, email, date, currency }

/// التحقق المنطقي والتحويل من نصّ الخلية.
class ImportValidator {
  /// يُرجع رسالة خطأ أو `null` عند نجاح التحقق.
  final String? Function(String? raw, Map<String, String> row)? validate;

  /// يحوّل القيمة النصية إلى القيمة النهائية المرسلة للخادم.
  final dynamic Function(String? raw, Map<String, String> row) convert;

  const ImportValidator({
    this.validate,
    required this.convert,
  });
}

/// جميع حقول العملاء.
const List<ImportField> customerFields = [
  ImportField(
    key: 'code',
    apiKey: 'code',
    label: 'الكود',
    aliases: [
      'الكود', 'الرمز', 'رقم العميل', 'كود العميل',
      'code', 'customer code', 'customer_code', 'customerCode',
    ],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'name',
    apiKey: 'name',
    label: 'الاسم',
    aliases: ['الاسم', 'اسم العميل', 'customer name', 'customer_name', 'name'],
    required: true,
  ),
  ImportField(
    key: 'phone',
    apiKey: 'phone',
    label: 'الهاتف',
    aliases: ['الهاتف', 'رقم الهاتف', 'phone', 'tel', 'telephone'],
  ),
  ImportField(
    key: 'mobile',
    apiKey: 'mobile',
    label: 'الجوال',
    aliases: ['الجوال', 'الموبايل', 'mobile', 'mobile_no', 'mobile_no'],
  ),
  ImportField(
    key: 'email',
    apiKey: 'email',
    label: 'البريد الإلكتروني',
    aliases: ['البريد', 'البريد الإلكتروني', 'ايميل', 'email', 'e-mail', 'mail'],
    type: ImportFieldType.email,
  ),
  ImportField(
    key: 'street',
    apiKey: 'street',
    label: 'العنوان / الشارع',
    aliases: ['العنوان', 'الشارع', 'street', 'address'],
  ),
  ImportField(
    key: 'city',
    apiKey: 'city',
    label: 'المدينة',
    aliases: ['المدينة', 'المحافظة', 'city'],
  ),
  ImportField(
    key: 'country',
    apiKey: 'country',
    label: 'الدولة',
    aliases: ['الدولة', 'البلد', 'country'],
  ),
  ImportField(
    key: 'tax_number',
    apiKey: 'tax_number',
    label: 'الرقم الضريبي',
    aliases: ['الرقم الضريبي', 'tax', 'tax number', 'tax_number', 'vat'],
  ),
  ImportField(
    key: 'credit_limit',
    apiKey: 'credit_limit',
    label: 'حد الائتمان',
    aliases: ['حد الائتمان', 'سقف الائتمان', 'credit limit', 'credit_limit'],
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'currency',
    apiKey: 'currency',
    label: 'العملة',
    aliases: ['العملة', 'currency', 'عملة'],
    type: ImportFieldType.currency,
  ),
  ImportField(
    key: 'branches',
    apiKey: 'branches',
    label: 'الفروع',
    aliases: [
      'الفروع', 'أسماء الفروع', 'فروع', 'فروع العميل',
      'branches', 'branch names', 'branch', 'locations', 'sites',
    ],
  ),
  ImportField(
    key: 'notes',
    apiKey: 'notes',
    label: 'ملاحظات',
    aliases: ['ملاحظات', 'بيان', 'notes', 'note'],
  ),
];

/// جميع حقول المنتجات.
const List<ImportField> productFields = [
  ImportField(
    key: 'code',
    apiKey: 'code',
    label: 'الكود',
    aliases: ['الكود', 'الرمز', 'كود المنتج', 'code', 'product code', 'sku'],
    required: true,
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'name',
    apiKey: 'name',
    label: 'الاسم',
    aliases: ['الاسم', 'اسم المنتج', 'product name', 'product_name', 'name'],
    required: true,
  ),
  ImportField(
    key: 'unit_price',
    apiKey: 'unit_price',
    label: 'سعر الوحدة',
    aliases: ['السعر', 'سعر الوحدة', 'unit price', 'price', 'unit_price', 'unitPrice'],
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'tax_rate',
    apiKey: 'tax_rate',
    label: 'نسبة الضريبة',
    aliases: ['نسبة الضريبة', 'الضريبة', 'tax', 'tax rate', 'tax_rate', 'vat'],
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'description',
    apiKey: 'description',
    label: 'الوصف',
    aliases: ['الوصف', 'description', 'details'],
  ),
  ImportField(
    key: 'category',
    apiKey: 'category',
    label: 'التصنيف',
    aliases: ['التصنيف', 'الفئة', 'category', 'categories', 'type'],
  ),
  ImportField(
    key: 'stock_quantity',
    apiKey: 'stock_quantity',
    label: 'الكمية في المخزون',
    aliases: ['الكمية', 'المخزون', 'stock', 'quantity', 'stock quantity', 'qty'],
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'low_stock_threshold',
    apiKey: 'low_stock_threshold',
    label: 'حد التنبيه',
    aliases: ['حد التنبيه', 'low stock', 'threshold'],
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'currency',
    apiKey: 'currency',
    label: 'العملة',
    aliases: ['العملة', 'currency', 'عملة'],
    type: ImportFieldType.currency,
  ),
];

/// حقول الفواتير: تتطلب عميلاً وسطراً واحداً على الأقل.
const List<ImportField> invoiceFields = [
  ImportField(
    key: 'customer_name',
    apiKey: 'customer_name',
    label: 'اسم العميل',
    aliases: ['اسم العميل', 'العميل', 'customer', 'customer name', 'customer_name'],
    required: true,
  ),
  ImportField(
    key: 'customer_id',
    apiKey: 'customer_id',
    label: 'رقم العميل',
    aliases: ['رقم العميل', 'كود العميل', 'customer id', 'customer_id'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'site_name',
    apiKey: 'site_name',
    label: 'اسم الفرع',
    aliases: [
      'اسم الفرع', 'الفرع', 'branch', 'site', 'site name', 'site_name',
      'branch name', 'branch_name', 'branchName', 'siteName',
      'الفروع', 'الفرع',
    ],
  ),
  ImportField(
    key: 'currency',
    apiKey: 'currency',
    label: 'العملة',
    aliases: ['العملة', 'currency', 'عملة'],
    type: ImportFieldType.currency,
  ),
  ImportField(
    key: 'payment_type',
    apiKey: 'payment_type',
    label: 'نوع الدفع',
    aliases: ['نوع الدفع', 'طريقة الدفع', 'payment', 'payment type', 'payment_type'],
  ),
  ImportField(
    key: 'date',
    apiKey: 'date',
    label: 'التاريخ',
    aliases: ['التاريخ', 'date', 'invoice date', 'invoice_date'],
    type: ImportFieldType.date,
  ),
  ImportField(
    key: 'product_code',
    apiKey: 'product_code',
    label: 'كود المنتج',
    aliases: ['كود المنتج', 'المنتج', 'product code', 'product_code', 'sku'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'product_name',
    apiKey: 'product_name',
    label: 'اسم المنتج',
    aliases: ['اسم المنتج', 'المنتج', 'product name', 'product_name'],
    required: true,
  ),
  ImportField(
    key: 'quantity',
    apiKey: 'quantity',
    label: 'الكمية',
    aliases: ['الكمية', 'quantity', 'qty', 'العدد'],
    required: true,
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'unit_price',
    apiKey: 'unit_price',
    label: 'سعر الوحدة',
    aliases: ['السعر', 'سعر الوحدة', 'unit price', 'unit_price', 'price'],
    required: true,
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'notes',
    apiKey: 'notes',
    label: 'ملاحظات',
    aliases: ['ملاحظات', 'notes', 'note'],
  ),
];

/// يحوّل القيمة النصية إلى عدد (دعم الفاصل/النقطة).
num? parseNumber(String? raw) {
  if (raw == null || raw.trim().isEmpty) return null;
  var s = raw.replaceAll(',', '').replaceAll('٫', '.').trim();
  if (s.trim().isEmpty) return null;
  final v = num.tryParse(s);
  if (v != null) return v;
  return null;
}

/// يوفّر قواعد التحقق والتحويل بشكل موحّد لكل كيان.
Map<String, ImportValidator> buildValidators(ImportEntityType type) {
  switch (type) {
    case ImportEntityType.customers:
      return {
        'code': ImportValidator(
          validate: (r, _) {
            if (r == null || r.trim().isEmpty) return null; // Will auto-generate
            if (r.trim().length < 3) return 'الكود يجب 3 أحرف على الأقل';
            return null;
          },
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'name': ImportValidator(
          validate: (r, _) =>
              (r == null || r.trim().length < 2) ? 'الاسم مطلوب (حرفان على الأقل)' : null,
          convert: (r, _) => r!.trim(),
        ),
        'phone': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'mobile': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'email': ImportValidator(
          validate: (r, _) {
            final v = _cleanOpt(r);
            if (v != null && !RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(v)) {
              return 'بريد إلكتروني غير صالح';
            }
            return null;
          },
          convert: (r, _) => _cleanOpt(r),
        ),
        'street': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'city': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'country': ImportValidator(convert: (r, _) {
          final v = _cleanOpt(r);
          return v ?? 'LB';
        }),
        'tax_number': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'credit_limit': ImportValidator(
          validate: (r, _) {
            final n = r == null ? null : parseNumber(r);
            if (r != null && r.trim().isNotEmpty && (n == null || n < 0)) {
              return 'قيمة رقمية غير صالحة';
            }
            return null;
          },
          convert: (r, _) => r == null || r.trim().isEmpty
              ? '0'
              : parseNumber(r).toString(),
        ),
        'currency': ImportValidator(
          validate: (r, _) {
            final v = _cleanOpt(r);
            if (v != null && v.length != 3) return 'رمز العملة 3 أحرف';
            return null;
          },
          convert: (r, _) => (_cleanOpt(r) ?? CurrencyHelper.baseCurrency).toUpperCase(),
        ),
        'branches': ImportValidator(
          validate: (r, _) {
            if (r == null) return null;
            for (final part in r.split(RegExp(r'[,;؛]'))) {
              if (part.trim().isEmpty) continue;
              if (part.trim().length < 2) return 'اسم فرع غير صالح (حرفان على الأقل)';
            }
            return null;
          },
          convert: (r, _) => _cleanOpt(r),
        ),
        'notes': ImportValidator(convert: (r, _) => _cleanOpt(r)),
      };
    case ImportEntityType.products:
      return {
        'code': ImportValidator(
          validate: (r, _) =>
              (r == null || r.trim().isEmpty) ? 'الكود مطلوب' : null,
          convert: (r, _) => r!.trim(),
        ),
        'name': ImportValidator(
          validate: (r, _) =>
              (r == null || r.trim().length < 2) ? 'الاسم مطلوب (حرفان على الأقل)' : null,
          convert: (r, _) => r!.trim(),
        ),
        'unit_price': ImportValidator(
          validate: (r, _) {
            final n = r == null ? null : parseNumber(r);
            if (r != null && r.trim().isNotEmpty && (n == null || n < 0)) {
              return 'قيمة رقمية غير صالحة';
            }
            return null;
          },
          convert: (r, _) => r == null || r.trim().isEmpty ? '0' : parseNumber(r).toString(),
        ),
        'tax_rate': ImportValidator(
          validate: (r, _) {
            final n = r == null ? null : parseNumber(r);
            if (r != null && r.trim().isNotEmpty && (n == null || n < 0)) {
              return 'قيمة رقمية غير صالحة';
            }
            return null;
          },
          convert: (r, _) => r == null || r.trim().isEmpty ? '0' : parseNumber(r).toString(),
        ),
        'description': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'category': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'stock_quantity': ImportValidator(
          validate: (r, _) {
            final n = r == null ? null : parseNumber(r);
            if (r != null && r.trim().isNotEmpty && (n == null || n < 0)) {
              return 'قيمة رقمية غير صالحة';
            }
            return null;
          },
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null ? 0 : n.toInt()).toString();
          },
        ),
        'low_stock_threshold': ImportValidator(
          validate: (r, _) {
            final n = r == null ? null : parseNumber(r);
            if (r != null && r.trim().isNotEmpty && (n == null || n < 0)) {
              return 'قيمة رقمية غير صالحة';
            }
            return null;
          },
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null ? 10 : n.toInt()).toString();
          },
        ),
        'currency': ImportValidator(
          validate: (r, _) {
            final v = _cleanOpt(r);
            if (v != null && v.length != 3) return 'رمز العملة 3 أحرف';
            return null;
          },
          convert: (r, _) => (_cleanOpt(r) ?? CurrencyHelper.baseCurrency).toUpperCase(),
        ),
      };
    case ImportEntityType.invoices:
      return {
        'customer_name': ImportValidator(
          validate: (r, _) =>
              (r == null || r.trim().length < 2) ? 'اسم العميل مطلوب' : null,
          convert: (r, _) => r!.trim(),
        ),
        'customer_id': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'site_name': ImportValidator(
          validate: (r, _) {
            if (r == null || r.trim().isEmpty) return null;
            if (r.trim().length < 2) return 'اسم الفرع يجب حرفين على الأقل';
            return null;
          },
          convert: (r, _) => _cleanOpt(r),
        ),
        'currency': ImportValidator(
          validate: (r, _) {
            final v = _cleanOpt(r);
            if (v != null && v.length != 3) return 'رمز العملة 3 أحرف';
            return null;
          },
          convert: (r, _) => (_cleanOpt(r) ?? CurrencyHelper.baseCurrency).toUpperCase(),
        ),
        'payment_type': ImportValidator(
          validate: (r, _) {
            final v = _cleanOpt(r);
            if (v != null &&
                !['cash', 'credit', 'check', 'card'].contains(v.toLowerCase())) {
              return 'نوع دفع غير صالح (cash/credit/check/card)';
            }
            return null;
          },
          convert: (r, _) => (_cleanOpt(r) ?? 'cash').toLowerCase(),
        ),
        'date': ImportValidator(
          validate: (r, _) {
            final v = _cleanOpt(r);
            if (v != null && _parseDate(v) == null) return 'تاريخ غير صالح';
            return null;
          },
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null) return null;
            final d = _parseDate(v);
            return d == null ? null : '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
          },
        ),
        'product_code': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'product_name': ImportValidator(
          validate: (r, _) =>
              (r == null || r.trim().isEmpty) ? 'اسم المنتج مطلوب' : null,
          convert: (r, _) => r!.trim(),
        ),
        'quantity': ImportValidator(
          validate: (r, _) {
            final n = r == null ? null : parseNumber(r);
            if (n == null || n <= 0) return 'الكمية مطلوبة وأكبر من صفر';
            return null;
          },
          convert: (r, _) => parseNumber(r).toString(),
        ),
        'unit_price': ImportValidator(
          validate: (r, _) {
            final n = r == null ? null : parseNumber(r);
            if (n == null || n < 0) return 'سعر الوحدة مطلوب';
            return null;
          },
          convert: (r, _) => parseNumber(r).toString(),
        ),
        'notes': ImportValidator(convert: (r, _) => _cleanOpt(r)),
      };
  }
}

String? _cleanOpt(String? raw) {
  if (raw == null) return null;
  final t = raw.trim();
  return t.isEmpty ? null : t;
}

DateTime? _parseDate(String v) {
  final s = v.trim().replaceAll('/', '-').replaceAll('.', '-').replaceAll('  ', ' ');
  // Remove time component if present (e.g., "2023-08-01 12:00:00" -> "2023-08-01")
  final withoutTime = s.split(' ').first;
  // yyyy-MM-dd
  final m1 = RegExp(r'^(\d{4})-(\d{1,2})-(\d{1,2})$').firstMatch(withoutTime);
  if (m1 != null) {
    final y = int.parse(m1[1]!);
    final mo = int.parse(m1[2]!);
    final d = int.parse(m1[3]!);
    if (y > 1900 && y < 2100 && mo >= 1 && mo <= 12 && d >= 1 && d <= 31) {
      return DateTime(y, mo, d);
    }
  }
  // dd-MM-yyyy
  final m2 = RegExp(r'^(\d{1,2})-(\d{1,2})-(\d{4})$').firstMatch(withoutTime);
  if (m2 != null) {
    final y = int.parse(m2[3]!);
    final mo = int.parse(m2[2]!);
    final d = int.parse(m2[1]!);
    if (y > 1900 && y < 2100 && mo >= 1 && mo <= 12 && d >= 1 && d <= 31) {
      return DateTime(y, mo, d);
    }
  }
  // MM-dd-yyyy
  final m3 = RegExp(r'^(\d{1,2})-(\d{1,2})-(\d{4})$').firstMatch(withoutTime);
  if (m3 != null) {
    final mo = int.parse(m3[1]!);
    final d = int.parse(m3[2]!);
    final y = int.parse(m3[3]!);
    if (y > 1900 && y < 2100 && mo >= 1 && mo <= 12 && d >= 1 && d <= 31) {
      return DateTime(y, mo, d);
    }
  }
  return DateTime.tryParse(withoutTime);
}
