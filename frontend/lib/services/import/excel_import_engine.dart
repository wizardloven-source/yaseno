// lib/services/import/excel_import_engine.dart
// محرك استيراد إكسل ديناميكي: يقرأ ملف .xlsx، يكتشف رأس الجدول تلقائياً،
// يطابق الأعمدة مع الحقول، يتحقق من البيانات، ثم يستورد صفاً تلو الآخر
// مع إرسال تقدم دوري وجمع نتائج كل صف.
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:excel/excel.dart';
import 'package:flutter/foundation.dart';
import '../../utils/currency_helper.dart';

import '../api_service.dart';
import 'import_definitions.dart';

/// نتيجة تحليل ملف الإكسل (رؤوس الأعمدة + صفوف البيانات كخرائط أعمدة).
class ExcelAnalysis {
  final List<String> headers;
  final List<Map<String, String>> rows;

  /// فهرس صف الرأس (0-بعد) كما اكتشفه المحرك؛ يُرسَل للخادم مع خيارات الاستيراد.
  final int headerIndex;

  const ExcelAnalysis({
    required this.headers,
    required this.rows,
    this.headerIndex = 0,
  });
}

/// نتيجة استيراد صف واحد.
class RowResult {
  final int rowNumber;
  final String? error;

  RowResult.success(this.rowNumber) : error = null;
  RowResult.failure(this.rowNumber, this.error);

  bool get success => error == null;
}

/// نتيجة الاستيراد الإجمالية.
class ImportSummary {
  final int total;
  final int success;
  final int failed;
  final List<RowResult> results;
  final int durationMs;

  const ImportSummary({
    required this.total,
    required this.success,
    required this.failed,
    required this.results,
    required this.durationMs,
  });
}

/// عميل مُحلّ (معرّف حقيقي + اسم) يُستخدم عند استيراد الفواتير.
class _ResolvedCustomer {
  final String id;
  final String name;

  _ResolvedCustomer(this.id, this.name);
}

class ExcelImportEngine {
  final ApiService _api = ApiService();

  // فهارس تُحمّل مرة واحدة خلال الجلسة لتمكين البحث بالكود/الاسم ومنع التكرار.
  Map<String, Map<String, dynamic>>? _customersByCode;
  final List<Map<String, dynamic>> _customerList = [];
  final Set<String> _customerIds = {};
  Map<String, Map<String, dynamic>>? _productsByCode;
  Set<String> _usedCodes = {};
  int _autoCodeCounter = 1;

  /// يقرأ ملف الإكسل ويحلّل أول ورقة إلى صفوف.
  Future<ExcelAnalysis> analyzeFile(Uint8List bytes, List<ImportField> fields,
      {int maxRows = 1000}) async {
    final excel = Excel.decodeBytes(bytes);
    if (excel.tables.isEmpty) {
      throw Exception('الملف لا يحتوي على أوراق عمل');
    }
    final sheet = excel.tables.values.first;
    final rows = sheet.rows;
    if (rows.isEmpty) {
      throw Exception('الملف فارغ');
    }

    // إيجاد صف الرأس: أول صف يحتوي على رأس معروف أو 2+ خلايا نصية.
    var headerIndex = 0;
    for (var i = 0; i < rows.length; i++) {
      final row = rows[i];
      final texts = row.map((c) => _cellText(c)).toList();
      final nonEmpty = texts.where((t) => t.trim().isNotEmpty).length;
      if (nonEmpty >= 2 && texts.any((t) => _isLikelyHeader(t, fields))) {
        headerIndex = i;
        break;
      }
    }

    final headerCells = rows[headerIndex].map((c) => _cellText(c)).toList();
    var last = headerCells.length - 1;
    while (last >= 0 && headerCells[last].trim().isEmpty) {
      last--;
    }
    final headers = headerCells.sublist(0, last + 1).map((h) => h.trim()).toList();

    final dataRows = <List<String>>[];
    var count = 0;
    for (var i = headerIndex + 1; i < rows.length; i++) {
      if (count >= maxRows) break;
      final texts = rows[i].map((c) => _cellText(c)).toList();
      if (texts.every((t) => t.trim().isEmpty)) continue;
      dataRows.add(texts);
      count++;
    }

    final result = <Map<String, String>>[];
    for (final row in dataRows) {
      final map = <String, String>{};
      for (var c = 0; c < headers.length; c++) {
        map['col$c'] = c < row.length ? row[c] : '';
      }
      result.add(map);
    }

    return ExcelAnalysis(headers: headers, rows: result, headerIndex: headerIndex);
  }

  /// مطابقة تلقائية: يحدد عمود كل حقل بناءً على عناوين الأعمدة.
  /// تقارن الرؤوس بعد التطبيع (الحالة/المسافات/الرموز) فتتطابق حتى مع
  /// تسميات مثل "CustomerCode" أو "رقم-العميل" (تعالج مشكلة مطابقة الأكواد/الأسماء).
  Map<String, int> autoMapColumns(List<String> headers, List<ImportField> fields) {
    final mapping = <String, int>{};
    final normalized = <String, List<String>>{
      for (final f in fields) f.key: f.aliases.map(_normalizeHeader).toList(),
    };
    for (final field in fields) {
      final aliases = normalized[field.key]!;
      for (var h = 0; h < headers.length; h++) {
        final header = _normalizeHeader(headers[h]);
        if (header.isEmpty) continue;
        if (aliases.any((a) => a == header)) {
          mapping[field.key] = h;
          break;
        }
      }
    }
    return mapping;
  }

  /// يستورد الصفوف فعلياً إلى الخادم مع التقدم والنتائج.
  /// يطبّق ديناميكيات الأكواد/الأسماء حسب نوع الكيان:
  /// - العملاء: توليد كود فريد أو تحديث العميل بنفس الكود.
  /// - المنتجات: كود+اسم متطابقان → تحديث؛ كود بكيان مختلف → كود جديد؛ كود جديد → إضافة.
  /// - الفواتير: حلّ العميل (بحث بالكود/الاسم في الخلفية) أو إنشاؤه تلقائياً.
  Future<ImportSummary> importRows({
    required ImportEntityType type,
    required List<ImportField> fields,
    required List<Map<String, String>> rows,
    required Map<String, int> columnMapping,
    String? baseCurrency,
    void Function(int done, int total)? onProgress,
  }) async {
    final validators = buildValidators(type);
    final start = DateTime.now();
    final results = <RowResult>[];
    var success = 0;

    // تحميل الفهارس حسب نوع الكيان (مرة واحدة لكل استيراد).
    if (type == ImportEntityType.customers || type == ImportEntityType.invoices) {
      await _ensureCustomerIndex();
    }
    if (type == ImportEntityType.products || type == ImportEntityType.invoices) {
      await _ensureProductIndex();
    }

    for (var i = 0; i < rows.length; i++) {
      final row = rows[i];
      final rowNumber = i + 2; // +1 لصف الرأس
      final values = _buildRowValues(row, fields, columnMapping);

      String? error;
      try {
        var skipPost = false;

        if (type == ImportEntityType.customers) {
          skipPost = await _handleCustomerRow(values, validators);
        } else if (type == ImportEntityType.products) {
          skipPost = await _handleProductRow(values, validators);
        } else if (type == ImportEntityType.invoices) {
          final resolved = await _resolveInvoiceCustomer(values);
          values['customer_id'] = resolved.id;
          values['customer_name'] = resolved.name;
        }

        if (skipPost) {
          success++;
        } else {
          final payload = _buildPayload(type, fields, values, validators,
              baseCurrency: baseCurrency);
          final response = await _api.post(type.apiEndpoint, data: payload);

          if (type == ImportEntityType.customers) {
            _indexCustomer(_createdRecord(response, values['code'] ?? '', values['name'] ?? ''));
            final branchError = await _createCustomerBranches(
              response,
              values,
              validators,
            );
            if (branchError != null) {
              throw ImportValidationException(branchError);
            }
          } else if (type == ImportEntityType.products) {
            _indexProduct(_createdRecord(response, values['code'] ?? '', values['name'] ?? ''));
          }

          success++;
        }
        results.add(RowResult.success(rowNumber));
      } on ImportValidationException catch (e) {
        error = e.message;
        results.add(RowResult.failure(rowNumber, error));
      } catch (e) {
        results.add(RowResult.failure(rowNumber, _cleanBackendError(e)));
      }

      onProgress?.call(i + 1, rows.length);

      // إتاحة تنفّس للواجهة عند الاستيراد الكبير.
      if ((i + 1) % 25 == 0) {
        await Future<void>.delayed(const Duration(milliseconds: 1));
      }
    }

    return ImportSummary(
      total: rows.length,
      success: success,
      failed: rows.length - success,
      results: results,
      durationMs: DateTime.now().difference(start).inMilliseconds,
    );
  }

  /// مسار «مركز الاستيراد»: يرفع بايتات الملف + خريطة المطابقة + الخيارات في
  /// طلب Multipart واحد، ويعالج الخادم كل الصفوف دفعة واحدة ويعيد ملخصاً شاملاً.
  /// ملاحظة: الصفوف في الرد مرقّمة حسب موقعها في ملف الإكسل الحقيقي (1-بعد).
  Future<ImportSummary> importFileViaServer({
    required ImportEntityType type,
    required Uint8List bytes,
    required Map<String, int> columnMapping,
    required int headerRow,
    String? baseCurrency,
    bool updateExisting = true,
  }) async {
    final response = await ApiService.staticPostMultipart(
      'import/${type.apiEndpoint}',
      fileBytes: bytes,
      formFields: {
        'mapping': jsonEncode(columnMapping),
        'options': jsonEncode({
          'base_currency': baseCurrency ?? CurrencyHelper.baseCurrency,
          'update_existing': updateExisting,
          'header_row': headerRow,
        }),
      },
    );

    final data = response;

    final rawResults = data['results'];
    final results = <RowResult>[];
    if (rawResults is List) {
      for (final rr in rawResults) {
        if (rr is! Map) continue;
        final row = rr['row'];
        final rowNumber = row is num ? row.toInt() : 0;
        final ok = rr['ok'] == true;
        final msg = rr['message'];
        if (ok) {
          results.add(RowResult.success(rowNumber));
        } else {
          results.add(RowResult.failure(rowNumber, msg?.toString() ?? ''));
        }
      }
    }

    final total = data['total'];
    final success = data['success'];
    final failed = data['failed'];
    final duration = data['durationMs'];
    return ImportSummary(
      total: total is num ? total.toInt() : results.length,
      success: success is num ? success.toInt() : results.where((r) => r.success).length,
      failed: failed is num ? failed.toInt() : results.where((r) => !r.success).length,
      results: results,
      durationMs: duration is num ? duration.toInt() : 0,
    );
  }

  // ===========================================================================
  // معالجات ديناميكيات الأكواد/الأسماء
  // ===========================================================================

  /// العميل: توليد كود فريد إن غاب، أو تحديث العميل ذي الكود نفسه.
  /// تُرجع `true` عند التحديث (دون إرسال POST للإنشاء).
  Future<bool> _handleCustomerRow(
    Map<String, String> values,
    Map<String, ImportValidator> validators,
  ) async {
    var code = _normalizeCode(values['code'] ?? '');
    // إصلاح ديناميكي: الكود الناقص/القصير/الطويل يتولّد تلقائياً ليطابق
    // قاعدة الخادم (3-20 حرفاً) بدل رفض الصف.
    if (code.isEmpty || code.length < 3 || code.length > 20) {
      code = _generateCustomerCode(values['name'] ?? '');
      values['code'] = code;
      _usedCodes.add(code);
      // الاسم الناقص يُولّد تلقائياً (حرفان على الأقل) بدل رفض الصف.
      final name = _cleanOpt(values['name']);
      if (name == null || name.length < 2) {
        values['name'] = 'عميل $code';
      }
      return false;
    }
    values['code'] = code;
    final existing = _customersByCode![code];
    if (existing == null) {
      _usedCodes.add(code);
      final name = _cleanOpt(values['name']);
      if (name == null || name.length < 2) {
        values['name'] = 'عميل $code';
      }
      return false;
    }

    // الكود موجود مسبقاً → تحديث بيانات العميل بدل رفض الصف.
    // في التحديث لا تُرسَل قيمة فارغة (اسم/بريد/هاتف) تجنباً لرفض الخادم.
    final upd = Map<String, dynamic>.from(
      _validatedSubset(const {'phone', 'mobile', 'email'}, values, validators),
    );
    final updName = _cleanOpt(values['name']);
    if (updName != null && updName.length >= 2) {
      upd.addAll(_validatedSubset(const {'name'}, values, validators));
    }
    if (upd.isNotEmpty) {
      final res = await _api.put('customers/${existing['id']}', data: upd);
      if (res['success'] == false) {
        throw ImportValidationException(
            res['message']?.toString() ?? 'فشل تحديث العميل');
      }
      final newName = upd['name']?.toString() ?? '';
      if (newName.isNotEmpty) {
        existing['name'] = newName;
        _customersByCode![_normalizeCode(code)] = existing;
      }
    }
    final branchError = await _createCustomerBranches(existing, values, validators);
    if (branchError != null) {
      throw ImportValidationException(branchError);
    }
    return true;
  }

  /// المنتج: كود+اسم متطابقان → تحديث؛ كود باسم آخر → كود جديد؛ كود جديد → إضافة.
  /// تُرجع `true` عند التحديث (دون إرسال POST للإنشاء).
  Future<bool> _handleProductRow(
    Map<String, String> values,
    Map<String, ImportValidator> validators,
  ) async {
    var code = _normalizeCode(values['code'] ?? '');
    final incomingName = values['name']?.trim() ?? '';
    // إصلاح ديناميكي: الكود الناقص يتولّد تلقائياً بدل رفض الصف.
    if (code.isEmpty) {
      code = _generateUniqueProductCode('PRD');
      values['code'] = code;
      if (incomingName.length < 2) {
        values['name'] = 'منتج $code';
      }
      _usedCodes.add(_normalizeCode(code));
      return false;
    }
    values['code'] = code;
    final existing = _productsByCode![code];

    if (existing == null) {
      _usedCodes.add(code);
      if (incomingName.length < 2) {
        values['name'] = 'منتج $code';
      }
      return false;
    }

    final sameName = incomingName.isEmpty ||
        _normalizeName(existing['name']?.toString() ?? '') ==
            _normalizeName(incomingName);
    if (sameName) {
      // تحديث المنتج الموجود (السعر/المخزون/الضريبة...). لا تُرسَل بيانات
      // جزئية فارغة قد تُفشل الخادم (مثل اسم فارغ).
      final upd = _validatedSubset(
        const {'unit_price', 'tax_rate', 'stock_quantity', 'description', 'category'},
        values,
        validators,
      );
      if (incomingName.isNotEmpty) {
        upd.addAll(_validatedSubset(const {'name'}, values, validators));
      }
      if (upd.isNotEmpty) {
        final res = await _api.put('products/${existing['id']}', data: upd);
        if (res['success'] == false) {
          throw ImportValidationException(
              res['message']?.toString() ?? 'فشل تحديث المنتج');
        }
      }
      return true;
    }

    // نفس الكود باسم مختلف → إضافة منتج جديد برمزٍ جديد.
    final newCode = _generateUniqueProductCode(code);
    values['code'] = newCode;
    _usedCodes.add(_normalizeCode(newCode));
    return false;
  }

  /// حلّ عميل الفاتورة: بحث بالكود/الاسم في الخلفية وإرجاع UUID الحقيقي؛
  /// وإن لم يوجد العميل يُنشأ تلقائياً (حسب اختيار المستخدم).
  Future<_ResolvedCustomer> _resolveInvoiceCustomer(Map<String, String> values) async {
    final code = _cleanOpt(values['customer_id']);
    final name = _cleanOpt(values['customer_name']);

    if (code != null) {
      final found = _customersByCode![_normalizeCode(code)] ?? await _findCustomerByCode(code);
      if (found != null) {
        return _ResolvedCustomer(found['id']!.toString(), found['name']!.toString());
      }
      final created = await _createCustomerAuto(name ?? 'عميل', code);
      return _ResolvedCustomer(created['id']!.toString(), created['name']!.toString());
    }

    // بدون كود: مطابقة بالاسم (بحث خلفي أيضاً).
    final normName = _normalizeName(name ?? '');
    var exact = _customerList
        .where((c) => _normalizeName(c['name']?.toString() ?? '') == normName)
        .toList();
    if (exact.length == 1) {
      return _ResolvedCustomer(exact.first['id']!.toString(), exact.first['name']!.toString());
    }
    if (exact.isEmpty && name != null) {
      exact = await _findCustomersByName(name);
      if (exact.length == 1) {
        return _ResolvedCustomer(exact.first['id']!.toString(), exact.first['name']!.toString());
      }
    }
    final created = await _createCustomerAuto(name ?? 'عميل', null);
    return _ResolvedCustomer(created['id']!.toString(), created['name']!.toString());
  }

  /// بحث خلفي بالكود عبر الخادم (نقطة /customers/search).
  Future<Map<String, dynamic>?> _findCustomerByCode(String code) async {
    try {
      final res = await _api.get('customers/search', queryParameters: {'q': code, 'limit': 25});
      final norm = _normalizeCode(code);
      for (final it in _itemsFrom(res)) {
        if (_normalizeCode(it['code']?.toString() ?? '') == norm) {
          _indexCustomer(it);
          return it;
        }
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> _findCustomersByName(String name) async {
    try {
      final res = await _api.get('customers/search', queryParameters: {'q': name, 'limit': 25});
      final norm = _normalizeName(name);
      var exact = _itemsFrom(res)
          .where((it) => _normalizeName(it['name']?.toString() ?? '') == norm)
          .toList();
      if (exact.isEmpty) exact = _itemsFrom(res);
      for (final it in exact) {
        _indexCustomer(it);
      }
      return exact;
    } catch (_) {
      return const [];
    }
  }

  /// إنشاء عميل تلقائياً مع كود فريد (إعادة المحاولة بكود آخر عند التعارض).
  Future<Map<String, dynamic>> _createCustomerAuto(String name, String? code) async {
    final cleanName = name.trim();
    var candidate = (code != null && code.trim().length >= 3 && code.trim().length <= 20)
        ? code.trim()
        : _generateCustomerCode(cleanName.isEmpty ? 'مستورد' : cleanName);
    for (var attempt = 0; attempt < 5; attempt++) {
      final res = await _api.post('customers', data: {
        'code': candidate,
        'name': cleanName,
        'country': 'LB',
      });
      if (res['success'] == false) {
        if (attempt >= 4) {
          throw ImportValidationException(
              'تعذّر إنشاء العميل تلقائياً (${res['message']?.toString() ?? ''})');
        }
        candidate = _generateCustomerCode(cleanName, attempt: attempt + 1);
        continue;
      }
      final record = Map<String, dynamic>.from(res);
      record['code'] = candidate;
      record['name'] = cleanName;
      _indexCustomer(record);
      return record;
    }
    throw ImportValidationException('تعذّر إنشاء العميل تلقائياً');
  }

  // ===========================================================================
  // الفهارس وتوليد الأكواد
  // ===========================================================================

  Future<void> _ensureCustomerIndex() async {
    if (_customersByCode != null) return;
    _customersByCode = {};
    _customerList.clear();
    _customerIds.clear();
    _usedCodes = {};
    try {
      final res = await _api.get('customers', queryParameters: {'limit': 1000});
      var maxNum = 0;
      for (final it in _itemsFrom(res)) {
        _indexCustomer(it);
        final code = it['code']?.toString() ?? '';
        final m = RegExp(r'(\d+)$').firstMatch(code);
        if (m != null) {
          final n = int.tryParse(m.group(1)!);
          if (n != null && n > maxNum) maxNum = n;
        }
      }
      _autoCodeCounter = maxNum + 1;
    } catch (_) {
      _autoCodeCounter = 1;
    }
  }

  Future<void> _ensureProductIndex() async {
    if (_productsByCode != null) return;
    _productsByCode = {};
    try {
      final res = await _api.get('products', queryParameters: {'limit': 1000});
      for (final it in _itemsFrom(res)) {
        _indexProduct(it);
      }
    } catch (_) {}
  }

  void _indexCustomer(Map<String, dynamic> c) {
    final code = _normalizeCode(c['code']?.toString() ?? '');
    if (code.isNotEmpty) {
      _customersByCode?[code] = c;
    }
    final id = c['id']?.toString() ?? '';
    if (!_customerIds.contains(id)) {
      _customerIds.add(id);
      _customerList.add(c);
    }
  }

  void _indexProduct(Map<String, dynamic> p) {
    final code = _normalizeCode(p['code']?.toString() ?? '');
    if (code.isNotEmpty) {
      _productsByCode?[code] = p;
    }
  }

  Map<String, dynamic> _createdRecord(Map<String, dynamic> response, String code, String name) {
    return {
      'id': response['id']?.toString() ?? '',
      'code': (response['code'] ?? code).toString(),
      'name': (response['name'] ?? name).toString(),
    };
  }

  /// توليد كود عميل فريد (سابقة من الاسم + رقم تسلسلي).
  String _generateCustomerCode(String name, {int attempt = 0}) {
    var clean = name
        .trim()
        .toUpperCase()
        .replaceAll(RegExp(r'[^\u0600-\u06FFA-Z0-9]'), '');
    if (clean.isEmpty) clean = 'CUS';
    var prefix = clean.length >= 3 ? clean.substring(0, 3) : clean;
    if (!RegExp(r'[A-Z]').hasMatch(prefix)) prefix = 'CUS$prefix';
    if (prefix.length > 6) prefix = prefix.substring(0, 6);

    var n = _autoCodeCounter + attempt;
    String candidate;
    do {
      candidate = '$prefix${n.toString().padLeft(4, '0')}';
      n++;
    } while (_usedCodes.contains(_normalizeCode(candidate)) ||
        _customersByCode!.containsKey(_normalizeCode(candidate)));
    _autoCodeCounter = n;
    return candidate;
  }

  /// توليد كود منتج فريد يختلف عن الكود الموجود بالاسم الآخر.
  String _generateUniqueProductCode(String code) {
    final base = _normalizeCode(code);
    if (base.isEmpty) return 'PRD-0001';
    var candidate = base;
    var i = 1;
    while (_productsByCode!.containsKey(_normalizeCode(candidate)) ||
        _usedCodes.contains(_normalizeCode(candidate))) {
      candidate = '$base-$i';
      i++;
    }
    return candidate;
  }

  /// يستخرج حقلاً فرعياً محوّلاً وموثّقاً (يُستخدم للتحديثات الجزئية).
  Map<String, dynamic> _validatedSubset(
    Set<String> keys,
    Map<String, String> values,
    Map<String, ImportValidator> validators,
  ) {
    final out = <String, dynamic>{};
    for (final key in keys) {
      final v = validators[key];
      if (v == null) continue;
      final valErr = v.validate?.call(values[key], values);
      if (valErr != null) {
        throw ImportValidationException('${_label(key)}: $valErr');
      }
      final converted = v.convert(values[key], values);
      if (converted != null) {
        out[key] = converted;
      }
    }
    return out;
  }

  Map<String, String> _buildRowValues(
    Map<String, String> row,
    List<ImportField> fields,
    Map<String, int> mapping,
  ) {
    final out = <String, String>{};
    for (final field in fields) {
      final col = mapping[field.key];
      if (col != null) {
        out[field.key] = row['col$col'] ?? '';
      }
    }
    return out;
  }

  Map<String, dynamic> _buildPayload(
    ImportEntityType type,
    List<ImportField> fields,
    Map<String, String> values,
    Map<String, ImportValidator> validators, {
    String? baseCurrency,
  }) {
    if (type == ImportEntityType.invoices) {
      return _buildInvoicePayload(values, validators);
    }
    final payload = <String, dynamic>{};
    for (final field in fields) {
      if (field.key == 'branches') continue;
      final v = validators[field.key]!;
      final raw = values[field.key];
      final valErr = v.validate?.call(raw, values);
      if (valErr != null) {
        throw ImportValidationException('${field.label}: $valErr');
      }
      final converted = v.convert(raw, values);
      if (converted != null) {
        payload[field.apiKey] = converted;
      }
    }
    return payload;
  }

  /// ينشئ فروع عميل من عمود "الفروع" (أسماء مفصولة بفواصل).
  /// يُرجع رسالة خطأ أو `null` عند النجاح.
  Future<String?> _createCustomerBranches(
    Map<String, dynamic> response,
    Map<String, String> values,
    Map<String, ImportValidator> validators,
  ) async {
    final raw = values['branches'];
    if (raw == null || raw.trim().isEmpty) return null;

    final names = raw
        .split(RegExp(r'[,;؛]'))
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
    if (names.isEmpty) return null;

    final customerId = response['id']?.toString();
    final customerCode = response['code']?.toString() ?? '';
    final customerName = response['name']?.toString() ?? values['name'] ?? '';

    if (customerId == null || customerId.isEmpty) {
      return 'تم إنشاء العميل لكن تعذّر جلب معرفه لإنشاء الفروع';
    }

    // يُورّث المدينة والهاتف من صف العميل إلى الفروع إن وُجدا.
    final city = _cleanOpt(values['city']);
    final phone = _cleanOpt(values['phone']);

    final failed = <String>[];
    for (var i = 0; i < names.length; i++) {
      final branchName = names[i];
      final code = customerCode.isEmpty
          ? 'BR${i + 1}'
          : '$customerCode-BR${i + 1}';
      try {
        await _api.post(
          'customers/$customerId/branches',
          data: {
            'code': code,
            'name': branchName,
            'customer_name': customerName,
            'customer_code': customerCode,
            if (city != null) 'city': city,
            if (phone != null) 'phone': phone,
          },
        );
      } catch (e) {
        failed.add('الفرع "$branchName" لم يُنشأ (${_cleanBackendError(e)})');
      }
    }

    if (failed.isNotEmpty) {
      return 'تم إنشاء العميل، لكن ${failed.join('، ')}';
    }
    return null;
  }

  Map<String, dynamic> _buildInvoicePayload(
    Map<String, String> values,
    Map<String, ImportValidator> validators,
  ) {
    final invoiceKeys = [
      'customer_name',
      'customer_id',
      'site_name',
      'currency',
      'payment_type',
      'date',
      'notes',
    ];
    final lineKeys = ['product_code', 'product_name', 'quantity', 'unit_price'];

    final payload = <String, dynamic>{};

    for (final key in invoiceKeys) {
      final v = validators[key]!;
      final raw = values[key];
      final valErr = v.validate?.call(raw, values);
      if (valErr != null) {
        throw ImportValidationException('${_label(key)}: $valErr');
      }
      final converted = v.convert(raw, values);
      if (converted != null) {
        payload[key] = converted;
      }
    }

    final line = <String, dynamic>{};
    for (final key in lineKeys) {
      final v = validators[key]!;
      final valErr = v.validate?.call(values[key], values);
      if (valErr != null) {
        throw ImportValidationException('${_label(key)}: $valErr');
      }
      final converted = v.convert(values[key], values);
      line[key] = converted;
    }
    line['currency'] = payload['currency'] ?? CurrencyHelper.baseCurrency;

    payload['lines'] = [line];
    return payload;
  }

  String _label(String key) {
    switch (key) {
      case 'customer_name':
        return 'اسم العميل';
      case 'customer_id':
        return 'رقم العميل';
      case 'site_name':
        return 'اسم الفرع';
      case 'currency':
        return 'العملة';
      case 'payment_type':
        return 'نوع الدفع';
      case 'date':
        return 'التاريخ';
      case 'notes':
        return 'ملاحظات';
      case 'product_code':
        return 'كود المنتج';
      case 'product_name':
        return 'اسم المنتج';
      case 'quantity':
        return 'الكمية';
      case 'unit_price':
        return 'سعر الوحدة';
      default:
        return key;
    }
  }

  String _cleanBackendError(Object e) {
    if (e is DioException) {
      final msg = e.message ?? '';
      if (msg.isNotEmpty) return msg.length > 200 ? '${msg.substring(0, 200)}...' : msg;
      final resp = e.response?.data;
      if (resp is Map) {
        final m = resp['message'] ?? resp['detail'];
        if (m is String && m.isNotEmpty) return m;
      }
      return 'فشل الاتصال بالخادم';
    }
    final msg = e.toString();
    return msg.length > 200 ? 'خطأ غير متوقع' : msg;
  }

  String? _cleanOpt(String? raw) {
    if (raw == null) return null;
    final t = raw.trim();
    return t.isEmpty ? null : t;
  }

  String _cellText(dynamic cell) {
    if (cell == null) return '';
    final v = cell.value;
    if (v == null) return '';
    if (v is TextCellValue) {
      return v.value.text ?? '';
    }
    if (v is DateCellValue) {
      return '${v.year.toString().padLeft(4, '0')}-${v.month.toString().padLeft(2, '0')}-${v.day.toString().padLeft(2, '0')}';
    }
    return v.toString();
  }
}

class ImportValidationException implements Exception {
  final String message;
  ImportValidationException(this.message);
  @override
  String toString() => message;
}

bool _isLikelyHeader(String cell, List<ImportField> fields) {
  final c = _normalizeHeader(cell);
  if (c.isEmpty) return false;
  for (final field in fields) {
    if (field.aliases.any((a) => _normalizeHeader(a) == c)) return true;
  }
  return ['name', 'code', 'quantity', 'price', 'الاسم', 'الكود', 'السعر', 'الكمية']
      .contains(c);
}

/// تطبيع رأس/نص للمطابقة: حروف صغيرة وإزالة المسافات والرموز.
String _normalizeHeader(String s) {
  return s.trim().toLowerCase().replaceAll(RegExp(r'[\s\-_/()\[\].,\\؛:]+'), '');
}

/// تطبيع كود للمقارنة: trim + أحرف كبيرة + إزالة مسافات داخلية.
String _normalizeCode(String s) {
  return s.trim().toUpperCase().replaceAll(RegExp(r'\s+'), '');
}

/// تطبيع اسم للمقارنة: trim + أحرف صغيرة + توحيد المسافات.
String _normalizeName(String s) {
  return s.trim().replaceAll(RegExp(r'\s+'), ' ').toLowerCase();
}

/// يستخرج قائمة العناصر من استجابة الخادم (data.items أو items مباشرة).
List<Map<String, dynamic>> _itemsFrom(Map<String, dynamic> res) {
  final items = res['items'];
  if (items is List) return items.cast<Map<String, dynamic>>();
  return const [];
}
