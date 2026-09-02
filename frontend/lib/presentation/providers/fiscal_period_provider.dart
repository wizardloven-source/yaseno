// frontend/lib/presentation/providers/fiscal_period_provider.dart
/// Provider للفترات المالية

import 'package:flutter/foundation.dart';
import '../../data/models/fiscal_period_model.dart';
import '../../services/api_service.dart';

class FiscalPeriodProvider extends ChangeNotifier {
  final ApiService _apiService;

  FiscalPeriodProvider({required ApiService apiService})
      : _apiService = apiService;

  List<FiscalPeriodModel> _periods = [];
  bool _isLoading = false;
  String? _error;

  List<FiscalPeriodModel> get periods => _periods;
  bool get isLoading => _isLoading;
  String? get error => _error;

  FiscalPeriodModel? get currentOpenPeriod {
    try {
      return _periods.firstWhere((p) => p.status == 'open');
    } catch (_) {
      return null;
    }
  }

  Future<void> loadPeriods() async {
    _setLoading(true);
    _error = null;

    try {
      final response = await _apiService.get('/fiscal-periods');
      final List<dynamic> data = response['data'] ?? [];
      _periods = data.map((e) => FiscalPeriodModel.fromJson(e)).toList();
      _periods.sort((a, b) => b.startDate.compareTo(a.startDate));
    } catch (e) {
      _error = 'فشل تحميل الفترات: $e';
    } finally {
      _setLoading(false);
    }
  }

  Future<void> createPeriod({
    required String name,
    required DateTime startDate,
    required DateTime endDate,
    required String periodType,
  }) async {
    try {
      final response = await _apiService.post('/fiscal-periods', data: {
        'name': name,
        'start_date': startDate.toIso8601String(),
        'end_date': endDate.toIso8601String(),
        'period_type': periodType,
      });
      if (response['success'] == true) {
        await loadPeriods();
      }
    } catch (e) {
      rethrow;
    }
  }

  Future<void> closePeriod(String periodId) async {
    try {
      final response = await _apiService.post('/fiscal-periods/$periodId/close');
      if (response['success'] == true) {
        await loadPeriods();
      }
    } catch (e) {
      rethrow;
    }
  }

  Future<void> reopenPeriod(String periodId) async {
    try {
      final response = await _apiService.post('/fiscal-periods/$periodId/reopen');
      if (response['success'] == true) {
        await loadPeriods();
      }
    } catch (e) {
      rethrow;
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }
}