import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

class ErrorUtils {
  /// Sanitizes raw exception messages into user-friendly Arabic messages
  static String sanitize(dynamic error) {
    // If it's a DioException carrying a server response, prefer the server's
    // detail message (e.g. "كلمة المرور يجب ألا تقل عن 10 أحرف").
    final serverDetail = _serverDetailFromDio(error);
    if (serverDetail != null) return serverDetail;

    final message = error.toString();

    // DioExceptions often contain URLs and status codes
    if (message.contains('DioException') || message.contains('DioError')) {
      if (message.contains('Connection refused') || message.contains('connecting')) {
        return 'لا يمكن الاتصال بالخادم. تحقق من اتصال الإنترنت.';
      }
      if (message.contains('401') || message.contains('Unauthorized')) {
        return 'انتهت صلاحية الجلسة. يرجى تسجيل الدخول مجدداً.';
      }
      if (message.contains('403') || message.contains('Forbidden')) {
        return 'ليس لديك صلاحية للقيام بهذا الإجراء.';
      }
      if (message.contains('404') || message.contains('Not Found')) {
        return 'العنصر المطلوب غير موجود.';
      }
      if (message.contains('422') || message.contains('Validation')) {
        return 'البيانات المدخلة غير صحيحة. تحقق من الحقول المطلوبة.';
      }
      if (message.contains('500') || message.contains('Internal Server Error')) {
        return 'خطأ في الخادم. يرجى المحاولة لاحقاً.';
      }
      if (message.contains('timeout') || message.contains('Timeout')) {
        return 'انتهت مهلة الاتصال. يرجى المحاولة مجدداً.';
      }
      return 'حدث خطأ في الاتصال. يرجى المحاولة مجدداً.';
    }

    if (message.contains('SocketException') || message.contains('Connection refused')) {
      return 'لا يمكن الاتصال بالخادم. تحقق من اتصال الإنترنت.';
    }

    if (message.contains('FormatException') || message.contains('JSON')) {
      return 'خطأ في تنسيق البيانات من الخادم.';
    }

    // Generic fallback - never expose raw exception
    if (message.length > 100) {
      return 'حدث خطأ غير متوقع. يرجى المحاولة مجدداً.';
    }

    // Short messages might be safe to show (like validation errors from backend)
    // But strip common technical prefixes
    String cleaned = message
        .replaceAll(RegExp(r'Exception:?\s*'), '')
        .replaceAll(RegExp(r'Error:?\s*'), '')
        .replaceAll(RegExp(r'DioException\[.*?\]:?\s*'), '')
        .replaceAll(RegExp(r'type\s+\w+\s+is not'), '')
        .trim();

    if (cleaned.isEmpty) {
      return 'حدث خطأ. يرجى المحاولة مجدداً.';
    }

    return cleaned;
  }

  /// يستخرج رسالة الخطأ التفصيلية التي أرسلها الخادم (detail) من DioException.
  static String? _serverDetailFromDio(dynamic error) {
    if (error is! DioException) return null;
    final data = error.response?.data;
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String && detail.trim().isNotEmpty) return detail.trim();
      if (detail is List && detail.isNotEmpty) {
        final first = detail.first;
        if (first is Map && (first['msg'] is String)) {
          return (first['msg'] as String).trim();
        }
      }
    }
    return null;
  }

  /// Shows a sanitized error in a SnackBar
  static void showErrorSnackBar(BuildContext context, dynamic error) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(sanitize(error)),
        backgroundColor: Colors.red.shade700,
        duration: const Duration(seconds: 4),
      ),
    );
  }
}
