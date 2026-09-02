// lib/services/import/excel_import_engine.dart
// محرك استيراد إكسل ديناميكي: يقرأ ملف .xlsx، يكتشف رأس الجدول تلقائياً،
// يطابق الأعمدة مع الحقول، يتحقق من البيانات، ثم يستورد صفاً تلو الآخر
// مع إرسال تقدم دوري وجمع نتائج كل صف.
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

  const ExcelAnalysis({required this.headers, required this.rows});
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

class ExcelImportEngine {
  final ApiService _api = ApiService();

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

    return ExcelAnalysis(headers: headers, rows: result);
  }

  /// مطابقة تلقائية: يحدد عمود كل حقل بناءً على عناوين الأعمدة.
  Map<String, int> autoMapColumns(List<String> headers, List<ImportField> fields) {
    final mapping = <String, int>{};
    for (final field in fields) {
      for (var h = 0; h < headers.length; h++) {
        final header = headers[h].trim().toLowerCase();
        if (field.aliases.any((a) => a.toLowerCase() == header)) {
          mapping[field.key] = h;
          break;
        }
      }
    }
    return mapping;
  }

  /// يستورد الصفوف فعلياً إلى الخادم مع التقدم والنتائج.
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

    // Auto-generate customer codes if needed
    int? autoCodeCounter;
    if (type == ImportEntityType.customers) {
      autoCodeCounter = await _getNextCustomerCodeCounter();
    }

    for (var i = 0; i < rows.length; i++) {
      final row = rows[i];
      final rowNumber = i + 2 + (0); // +1 لصف الرأس
      final values = _buildRowValues(row, fields, columnMapping);

      // Auto-generate customer code if empty
      if (type == ImportEntityType.customers) {
        final code = values['code'];
        if (code == null || code.trim().isEmpty) {
          final name = values['name'] ?? '';
          final prefix = name.isNotEmpty
              ? name.substring(0, name.length < 3 ? name.length : 3).toUpperCase()
              : 'CUS';
          values['code'] = '$prefix${autoCodeCounter.toString().padLeft(4, '0')}';
          autoCodeCounter = (autoCodeCounter ?? 1) + 1;
        }
      }

      String? error;
      Map<String, dynamic>? payload;
      try {
        payload = _buildPayload(type, fields, values, validators,
            baseCurrency: baseCurrency);
      } on ImportValidationException catch (e) {
        error = e.message;
      } catch (_) {
        error = 'خطأ غير متوقع في تحويل البيانات';
      }

      if (error != null) {
        results.add(RowResult.failure(rowNumber, error));
        onProgress?.call(i + 1, rows.length);
        continue;
      }

      try {
        final response = await _api.post(type.apiEndpoint, data: payload);
        if (type == ImportEntityType.customers) {
          final branchError = await _createCustomerBranches(
            response,
            values,
            validators,
          );
          if (branchError != null) {
            error = branchError;
          }
        }
        if (error != null) {
          results.add(RowResult.failure(rowNumber, error));
        } else {
          success++;
          results.add(RowResult.success(rowNumber));
        }
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
          : '${customerCode}-BR${i + 1}';
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

  /// Get the next counter for auto-generating customer codes.
  Future<int> _getNextCustomerCodeCounter() async {
    try {
      final response = await _api.get('customers', queryParameters: {'limit': 1000});
      final data = response['data'] ?? response;
      final items = data['items'] ?? data;
      if (items is! List) return 1;

      int maxNum = 0;
      for (final item in items) {
        final code = item['code']?.toString() ?? '';
        // Extract trailing numbers from code
        final match = RegExp(r'(\d+)$').firstMatch(code);
        if (match != null) {
          final num = int.tryParse(match.group(1)!);
          if (num != null && num > maxNum) maxNum = num;
        }
      }
      return maxNum + 1;
    } catch (_) {
      return 1;
    }
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
  final c = cell.trim().toLowerCase();
  for (final field in fields) {
    if (field.aliases.any((a) => a.toLowerCase() == c)) return true;
  }
  return ['name', 'code', 'quantity', 'price', 'الاسم', 'الكود', 'السعر', 'الكمية']
      .contains(c);
}
