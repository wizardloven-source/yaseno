// frontend/lib/data/repositories/dashboard_repository.dart
/// مستودع بيانات لوحة التحكم

import '../models/dashboard_models.dart';
import '../../services/api_service.dart';

class DashboardRepository {
  final ApiService _apiService;

  DashboardRepository({required ApiService apiService})
      : _apiService = apiService;

  /// جلب ملخص مؤشرات الأداء
  Future<Map<String, dynamic>> getKpiSummary() async {
    try {
      final response = await _apiService.get('/dashboard/kpi-summary');
      return response['data'] ?? {};
    } catch (e) {
      rethrow;
    }
  }

  /// جلب بيانات الرسم البياني الشهري
  Future<List<MonthlyChartData>> getMonthlyChart(int months) async {
    try {
      final response = await _apiService.get(
        '/dashboard/monthly-chart',
        queryParameters: {'months': months},
      );
      final List<dynamic> data = response['data'] ?? [];
      return data.map((e) => MonthlyChartData.fromJson(e)).toList();
    } catch (e) {
      rethrow;
    }
  }

  /// جلب آخر القيود
  Future<List<RecentEntryModel>> getRecentEntries(int limit) async {
    try {
      final response = await _apiService.get(
        '/journal-entries',
        queryParameters: {'limit': limit, 'order_by': '-created_at'},
      );
      final List<dynamic> data = response['data'] ?? [];
      return data.map((e) => RecentEntryModel.fromJson(e)).toList();
    } catch (e) {
      rethrow;
    }
  }

  /// جلب التنبيهات
  Future<List<AlertModel>> getAlerts() async {
    try {
      final response = await _apiService.get('/dashboard/alerts');
      final List<dynamic> data = response['data'] ?? [];
      return data.map((e) => AlertModel.fromJson(e)).toList();
    } catch (e) {
      return []; // لا نفشل إذا فشلت التنبيهات
    }
  }

  /// جلب معلومات المستخدم
  Future<Map<String, dynamic>> getUserInfo() async {
    try {
      final response = await _apiService.get('/auth/me');
      return response['data'] ?? {};
    } catch (e) {
      return {'name': 'مستخدم', 'unread_notifications': 0};
    }
  }
}