// lib/services/import/import_definitions.dart
// تعريفات حقول الاستيراد لكل كيان: الأسماء العربية/الإنجليزية للأعمدة،
// والمفاتيح الخلفية (snake_case)، وأدوات التحقق والتحويل.
//
// تُستخدم هذه التعريفات من قبل محرك الاستيراد لتحديد الأعمدة تلقائياً
// حتى لو اختلفت تسميات الرؤوس في ملف الإكسل (عربي/إنجليزي/أخرى).

import '../../utils/currency_helper.dart';

/// نوع البيانات الذي سيتم استيراده.
enum ImportEntityType {
  customers,
  products,
  invoices,
  suppliers,
  accounts,
  sites,
  centers,
  projects,
  currencies,
}

extension ImportEntityTypeX on ImportEntityType {
  String get title {
    switch (this) {
      case ImportEntityType.customers:
        return 'استيراد العملاء';
      case ImportEntityType.products:
        return 'استيراد المنتجات';
      case ImportEntityType.invoices:
        return 'استيراد الفواتير';
      case ImportEntityType.suppliers:
        return 'استيراد الموردين';
      case ImportEntityType.accounts:
        return 'استيراد دليل الحسابات';
      case ImportEntityType.sites:
        return 'استيراد المواقع';
      case ImportEntityType.centers:
        return 'استيراد مراكز التكلفة';
      case ImportEntityType.projects:
        return 'استيراد المشاريع';
      case ImportEntityType.currencies:
        return 'استيراد العملات';
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
      case ImportEntityType.suppliers:
        return 'مورد';
      case ImportEntityType.accounts:
        return 'حساب';
      case ImportEntityType.sites:
        return 'موقع';
      case ImportEntityType.centers:
        return 'مركز تكلفة';
      case ImportEntityType.projects:
        return 'مشروع';
      case ImportEntityType.currencies:
        return 'عملة';
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
      case ImportEntityType.suppliers:
        return 'suppliers';
      case ImportEntityType.accounts:
        return 'accounts';
      case ImportEntityType.sites:
        return 'sites';
      case ImportEntityType.centers:
        return 'centers';
      case ImportEntityType.projects:
        return 'projects';
      case ImportEntityType.currencies:
        return 'currencies';
    }
  }

  /// قائمة حقول هذا الكيان للاستيراد.
  List<ImportField> get fields => _fieldsOf(this);
}

List<ImportField> _fieldsOf(ImportEntityType type) {
  switch (type) {
    case ImportEntityType.customers:
      return customerFields;
    case ImportEntityType.products:
      return productFields;
    case ImportEntityType.invoices:
      return invoiceFields;
    case ImportEntityType.suppliers:
      return supplierFields;
    case ImportEntityType.accounts:
      return accountFields;
    case ImportEntityType.sites:
      return siteFields;
    case ImportEntityType.centers:
      return centerFields;
    case ImportEntityType.projects:
      return projectFields;
    case ImportEntityType.currencies:
      return currencyFields;
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
      'اسم الفرع', 'الأفرع',
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

/// جميع حقول الموردين.
const List<ImportField> supplierFields = [
  ImportField(
    key: 'code',
    apiKey: 'code',
    label: 'الكود',
    aliases: ['الكود', 'الرمز', 'كود المورد', 'code', 'supplier code', 'supplier_code'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'name',
    apiKey: 'name',
    label: 'الاسم',
    aliases: ['الاسم', 'اسم المورد', 'supplier name', 'supplier_name', 'name'],
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
    aliases: ['الجوال', 'الموبايل', 'mobile', 'mobile_no'],
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
    aliases: ['حد الائتمان', 'credit limit', 'credit_limit'],
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
    key: 'notes',
    apiKey: 'notes',
    label: 'ملاحظات',
    aliases: ['ملاحظات', 'بيان', 'notes', 'note'],
  ),
];

/// جميع حقول دليل الحسابات.
const List<ImportField> accountFields = [
  ImportField(
    key: 'code',
    apiKey: 'code',
    label: 'الكود',
    aliases: ['الكود', 'الرمز', 'كود الحساب', 'code', 'account code', 'account_code'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'name',
    apiKey: 'name',
    label: 'الاسم',
    aliases: ['الاسم', 'اسم الحساب', 'account name', 'account_name', 'name'],
  ),
  ImportField(
    key: 'account_type',
    apiKey: 'account_type',
    label: 'نوع الحساب',
    aliases: ['نوع الحساب', 'account type', 'account_type', 'type'],
  ),
  ImportField(
    key: 'parent_code',
    apiKey: 'parent_code',
    label: 'الحساب الرئيسي',
    aliases: ['الحساب الرئيسي', 'الحساب الأب', 'parent', 'parent account', 'parent_code'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'description',
    apiKey: 'description',
    label: 'الوصف',
    aliases: ['الوصف', 'description', 'details'],
  ),
  ImportField(
    key: 'currency',
    apiKey: 'currency',
    label: 'العملة',
    aliases: ['العملة', 'currency', 'عملة'],
    type: ImportFieldType.currency,
  ),
  ImportField(
    key: 'is_active',
    apiKey: 'is_active',
    label: 'مفعل',
    aliases: ['مفعل', 'active', 'is_active'],
  ),
];

/// جميع حقول المواقع.
const List<ImportField> siteFields = [
  ImportField(
    key: 'code',
    apiKey: 'code',
    label: 'الكود',
    aliases: ['الكود', 'الرمز', 'كود الموقع', 'code', 'site code', 'site_code'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'name',
    apiKey: 'name',
    label: 'الاسم',
    aliases: ['الاسم', 'اسم الموقع', 'site name', 'site_name', 'name'],
  ),
  ImportField(
    key: 'site_type',
    apiKey: 'site_type',
    label: 'نوع الموقع',
    aliases: ['نوع الموقع', 'site type', 'site_type', 'type'],
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
    key: 'phone',
    apiKey: 'phone',
    label: 'الهاتف',
    aliases: ['الهاتف', 'رقم الهاتف', 'phone', 'tel'],
  ),
  ImportField(
    key: 'mobile',
    apiKey: 'mobile',
    label: 'الجوال',
    aliases: ['الجوال', 'الموبايل', 'mobile', 'mobile_no'],
  ),
  ImportField(
    key: 'email',
    apiKey: 'email',
    label: 'البريد الإلكتروني',
    aliases: ['البريد', 'ايميل', 'email', 'e-mail', 'mail'],
    type: ImportFieldType.email,
  ),
  ImportField(
    key: 'contact_person',
    apiKey: 'contact_person',
    label: 'المسؤول / المدير',
    aliases: [
      'شخص الاتصال', 'المسؤول', 'مدير الموقع', 'contact person', 'contact_person',
      'manager name', 'manager_name',
    ],
  ),
  ImportField(
    key: 'notes',
    apiKey: 'notes',
    label: 'ملاحظات',
    aliases: ['ملاحظات', 'notes', 'note'],
  ),
  ImportField(
    key: 'is_default',
    apiKey: 'is_default',
    label: 'الافتراضي',
    aliases: ['الافتراضي', 'الرئيسي', 'default', 'is_default'],
  ),
];

/// جميع حقول مراكز التكلفة.
const List<ImportField> centerFields = [
  ImportField(
    key: 'code',
    apiKey: 'code',
    label: 'الكود',
    aliases: ['الكود', 'الرمز', 'كود المركز', 'code', 'center code', 'center_code'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'name',
    apiKey: 'name',
    label: 'الاسم',
    aliases: ['الاسم', 'اسم المركز', 'center name', 'center_name', 'name'],
  ),
  ImportField(
    key: 'center_type',
    apiKey: 'center_type',
    label: 'نوع المركز',
    aliases: ['نوع المركز', 'center type', 'center_type', 'type'],
  ),
  ImportField(
    key: 'parent_code',
    apiKey: 'parent_code',
    label: 'المركز الرئيسي',
    aliases: ['المركز الرئيسي', 'المركز الأب', 'parent', 'parent center', 'parent_code'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'manager_name',
    apiKey: 'manager_name',
    label: 'مدير المركز',
    aliases: ['مدير المركز', 'manager', 'manager_name'],
  ),
  ImportField(
    key: 'department',
    apiKey: 'department',
    label: 'القسم / الإدارة',
    aliases: ['القسم', 'الإدارة', 'department'],
  ),
  ImportField(
    key: 'budget_amount',
    apiKey: 'budget_amount',
    label: 'الميزانية',
    aliases: ['الميزانية', 'budget', 'budget amount', 'budget_amount'],
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'budget_currency',
    apiKey: 'budget_currency',
    label: 'عملة الميزانية',
    aliases: ['عملة الميزانية', 'budget currency', 'budget_currency'],
    type: ImportFieldType.currency,
  ),
  ImportField(
    key: 'description',
    apiKey: 'description',
    label: 'الوصف',
    aliases: ['الوصف', 'description', 'details'],
  ),
];

/// جميع حقول المشاريع.
const List<ImportField> projectFields = [
  ImportField(
    key: 'code',
    apiKey: 'code',
    label: 'الكود',
    aliases: ['الكود', 'الرمز', 'كود المشروع', 'code', 'project code', 'project_code'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'name',
    apiKey: 'name',
    label: 'الاسم',
    aliases: ['الاسم', 'اسم المشروع', 'project name', 'project_name', 'name'],
  ),
  ImportField(
    key: 'description',
    apiKey: 'description',
    label: 'الوصف',
    aliases: ['الوصف', 'description', 'details'],
  ),
  ImportField(
    key: 'customer_name',
    apiKey: 'customer_name',
    label: 'العميل',
    aliases: ['العميل', 'اسم العميل', 'customer', 'customer_name'],
  ),
  ImportField(
    key: 'manager_name',
    apiKey: 'manager_name',
    label: 'مدير المشروع',
    aliases: ['مدير المشروع', 'manager', 'manager_name'],
  ),
  ImportField(
    key: 'budget_amount',
    apiKey: 'budget_amount',
    label: 'الميزانية',
    aliases: ['الميزانية', 'budget', 'budget amount', 'budget_amount'],
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'budget_currency',
    apiKey: 'budget_currency',
    label: 'عملة الميزانية',
    aliases: ['عملة الميزانية', 'budget currency', 'budget_currency'],
    type: ImportFieldType.currency,
  ),
  ImportField(
    key: 'start_date',
    apiKey: 'start_date',
    label: 'تاريخ البدء',
    aliases: ['تاريخ البدء', 'البداية', 'start date', 'start_date'],
    type: ImportFieldType.date,
  ),
  ImportField(
    key: 'end_date',
    apiKey: 'end_date',
    label: 'تاريخ الانتهاء',
    aliases: ['تاريخ الانتهاء', 'النهاية', 'end date', 'end_date'],
    type: ImportFieldType.date,
  ),
  ImportField(
    key: 'status',
    apiKey: 'status',
    label: 'الحالة',
    aliases: ['الحالة', 'status'],
  ),
  ImportField(
    key: 'tags',
    apiKey: 'tags',
    label: 'الوسوم',
    aliases: ['الوسوم', 'tags', 'tag'],
  ),
];

/// جميع حقول العملات.
const List<ImportField> currencyFields = [
  ImportField(
    key: 'code',
    apiKey: 'code',
    label: 'الكود',
    aliases: ['الكود', 'الرمز', 'كود العملة', 'code', 'currency code', 'currency_code', 'currencyCode'],
    type: ImportFieldType.code,
  ),
  ImportField(
    key: 'name',
    apiKey: 'name',
    label: 'الاسم',
    aliases: ['الاسم', 'اسم العملة', 'currency name', 'currency_name', 'name'],
  ),
  ImportField(
    key: 'symbol',
    apiKey: 'symbol',
    label: 'الرمز',
    aliases: ['الرمز', 'symbol'],
  ),
  ImportField(
    key: 'decimal_places',
    apiKey: 'decimal_places',
    label: 'المنازل العشرية',
    aliases: ['المنازل العشرية', 'decimal', 'decimal places', 'decimal_places'],
    type: ImportFieldType.number,
  ),
  ImportField(
    key: 'is_base',
    apiKey: 'is_base',
    label: 'الأساسية',
    aliases: ['الأساسية', 'الرئيسية', 'base', 'is_base'],
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
          // إصلاح ديناميكي: الكود القصير/الملوّث يُعاد توليده تلقائياً في المحرك
          // بدل رفض الصف (قاعدة الخادم: 3-20 حرفاً).
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'name': ImportValidator(
          // إصلاح ديناميكي: الاسم الناقص يُولّد تلقائياً في المحرك بدل الرفض.
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'phone': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'mobile': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'email': ImportValidator(
          validate: (r, _) => null, // البريد غير الصالح يُتجاهل بدل رفض الصف.
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null) return null;
            if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(v)) return null;
            return v;
          },
        ),
        'street': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'city': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'country': ImportValidator(convert: (r, _) {
          final v = _cleanOpt(r);
          return v ?? 'LB';
        }),
        'tax_number': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'credit_limit': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            if (r == null || r.trim().isEmpty) return '0';
            final n = parseNumber(r);
            return (n == null || n < 0) ? '0' : n.toString();
          },
        ),
        'currency': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || v.length != 3) {
              return CurrencyHelper.baseCurrency.toUpperCase();
            }
            return v.toUpperCase();
          },
        ),
        'branches': ImportValidator(
          validate: (r, _) {
            if (r == null) return null;
            for (final part in r.split(RegExp(r'[,;،.\-_\n\r\t]'))) {
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
          validate: (r, _) => null,
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null || n < 0) ? '0' : n.toString();
          },
        ),
        'tax_rate': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null || n < 0) ? '0' : n.toString();
          },
        ),
        'description': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'category': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'stock_quantity': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null || n < 0) ? '0' : n.toInt().toString();
          },
        ),
        'low_stock_threshold': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null || n < 0) ? '10' : n.toInt().toString();
          },
        ),
        'currency': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || v.length != 3) {
              return CurrencyHelper.baseCurrency.toUpperCase();
            }
            return v.toUpperCase();
          },
        ),
      };
    case ImportEntityType.suppliers:
      return {
        'code': ImportValidator(
          // توليد تلقائي في الخادم عند الغياب/الطول غير الصالح.
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'name': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'phone': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'mobile': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'email': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null) return null;
            if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(v)) return null;
            return v;
          },
        ),
        'street': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'city': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'country': ImportValidator(convert: (r, _) => _cleanOpt(r) ?? 'LB'),
        'tax_number': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'credit_limit': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            if (r == null || r.trim().isEmpty) return '0';
            final n = parseNumber(r);
            return (n == null || n < 0) ? '0' : n.toString();
          },
        ),
        'currency': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || v.length != 3) {
              return CurrencyHelper.baseCurrency.toUpperCase();
            }
            return v.toUpperCase();
          },
        ),
        'notes': ImportValidator(convert: (r, _) => _cleanOpt(r)),
      };
    case ImportEntityType.accounts:
      return {
        'code': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'name': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'account_type': ImportValidator(
          validate: (r, _) => null, // غير الصالح يتحول إلى asset في الخادم.
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null) return '';
            return v;
          },
        ),
        'parent_code': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'description': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'currency': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || v.length != 3) {
              return CurrencyHelper.baseCurrency.toUpperCase();
            }
            return v.toUpperCase();
          },
        ),
        'is_active': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => _parseBoolValue(r) ? 'true' : 'false',
        ),
      };
    case ImportEntityType.sites:
      return {
        'code': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'name': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'site_type': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || !['general', 'store', 'branch', 'warehouse'].contains(v.toLowerCase())) {
              return 'general';
            }
            return v.toLowerCase();
          },
        ),
        'street': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'city': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'country': ImportValidator(convert: (r, _) => _cleanOpt(r) ?? 'LB'),
        'phone': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'mobile': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'email': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null) return null;
            if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(v)) return null;
            return v;
          },
        ),
        'contact_person': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'notes': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'is_default': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => _parseBoolValue(r) ? 'true' : 'false',
        ),
      };
    case ImportEntityType.centers:
      return {
        'code': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'name': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'center_type': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || !['cost', 'profit', 'both'].contains(v.toLowerCase())) {
              return 'cost';
            }
            return v.toLowerCase();
          },
        ),
        'parent_code': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'manager_name': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'department': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'budget_amount': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            if (r == null || r.trim().isEmpty) return '0';
            final n = parseNumber(r);
            return (n == null || n < 0) ? '0' : n.toString();
          },
        ),
        'budget_currency': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || v.length != 3) {
              return CurrencyHelper.baseCurrency.toUpperCase();
            }
            return v.toUpperCase();
          },
        ),
        'description': ImportValidator(convert: (r, _) => _cleanOpt(r)),
      };
    case ImportEntityType.projects:
      return {
        'code': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => _cleanOpt(r),
        ),
        'name': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => _cleanOpt(r),
        ),
        'description': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'customer_name': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'manager_name': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'budget_amount': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            if (r == null || r.trim().isEmpty) return '0';
            final n = parseNumber(r);
            return (n == null || n < 0) ? '0' : n.toString();
          },
        ),
        'budget_currency': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || v.length != 3) {
              return CurrencyHelper.baseCurrency.toUpperCase();
            }
            return v.toUpperCase();
          },
        ),
        'start_date': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null) return null;
            final d = _parseDate(v);
            return d == null ? null : '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
          },
        ),
        'end_date': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null) return null;
            final d = _parseDate(v);
            return d == null ? null : '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
          },
        ),
        'status': ImportValidator(
          validate: (r, _) => null, // غير الصالح في الخادم يُرفض الصف بوضوح.
          convert: (r, _) => _cleanOpt(r) ?? 'planning',
        ),
        'tags': ImportValidator(convert: (r, _) => _cleanOpt(r)),
      };
    case ImportEntityType.currencies:
      return {
        'code': ImportValidator(
          validate: (r, _) => null, // يُشتق من الاسم في الخادم عند غيابه.
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || v.length != 3 || !RegExp(r'^[a-zA-Z]{3}$').hasMatch(v)) {
              return '';
            }
            return v.toUpperCase();
          },
        ),
        'name': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => r == null || r.trim().isEmpty ? '' : r.trim(),
        ),
        'symbol': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'decimal_places': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null || n < 0) ? '2' : n.toInt().toString();
          },
        ),
        'is_base': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) => _parseBoolValue(r) ? 'true' : 'false',
        ),
      };
    case ImportEntityType.invoices:
      return {
        'customer_name': ImportValidator(
          validate: (r, _) => null, // يُملأ تلقائياً من المحرك (حلّ العميل/إنشاؤه).
          convert: (r, _) => _cleanOpt(r) ?? '',
        ),
        'customer_id': ImportValidator(convert: (r, _) => _cleanOpt(r)),
        'site_name': ImportValidator(
          validate: (r, _) => null, // غير المكتمل يُتجاهل بدل رفض الفاتورة.
          convert: (r, _) => _cleanOpt(r),
        ),
        'currency': ImportValidator(
          validate: (r, _) => null,
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null || v.length != 3) {
              return CurrencyHelper.baseCurrency.toUpperCase();
            }
            return v.toUpperCase();
          },
        ),
        'payment_type': ImportValidator(
          validate: (r, _) => null, // غير الصالح يتحول إلى cash بدل الرفض.
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v != null &&
                ['cash', 'credit', 'check', 'card'].contains(v.toLowerCase())) {
              return v.toLowerCase();
            }
            return 'cash';
          },
        ),
        'date': ImportValidator(
          validate: (r, _) => null, // غير الصالح يتجاهل التاريخ (خادم يستخدم الافتراضي).
          convert: (r, _) {
            final v = _cleanOpt(r);
            if (v == null) return null;
            final d = _parseDate(v);
            return d == null ? null : '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
          },
        ),
        'product_code': ImportValidator(
          validate: (r, _) => null,
          convert: (r, row) {
            final v = _cleanOpt(r);
            if (v != null) return v;
            // بدون كود → يولّد من اسم المنتج كبديل ديناميكي.
            final n = _cleanOpt(row['product_name']);
            return n != null && n.length <= 50 ? n : 'NOCODE';
          },
        ),
        'product_name': ImportValidator(
          validate: (r, _) => null, // الناقص يُولّد من الكود بدل الرفض.
          convert: (r, row) {
            final v = _cleanOpt(r);
            if (v != null) return v;
            final c = _cleanOpt(row['product_code']);
            return c == null ? 'منتج' : 'منتج $c';
          },
        ),
        'quantity': ImportValidator(
          validate: (r, _) => null, // الناقص/الخاطئ → 1 افتراضياً بدل الرفض.
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null || n <= 0) ? '1' : n.toString();
          },
        ),
        'unit_price': ImportValidator(
          validate: (r, _) => null, // الناقص → 0 افتراضياً بدل الرفض.
          convert: (r, _) {
            final n = parseNumber(r);
            return (n == null || n < 0) ? '0' : n.toString();
          },
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

bool _parseBoolValue(String? raw) {
  if (raw == null) return false;
  final s = raw.trim().toLowerCase();
  if (['1', 'true', 'yes', 'y', 'نعم', 'مفعل', 'active'].contains(s)) return true;
  return false;
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
