// frontend/lib/presentation/providers/dashboard_provider.dart
/// Provider للوحة التحكم الرئيسية

import 'package:flutter/foundation.dart';
import 'package:decimal/decimal.dart';
import '../../data/repositories/dashboard_repository.dart';
import '../../data/models/dashboard_models.dart';
import '../../utils/money_utils.dart';

class DashboardProvider extends ChangeNotifier {
  final DashboardRepository _repository;

  DashboardProvider({required DashboardRepository repository})
      : _repository = repository;

  // ==================== State ====================
  bool _isLoading = false;
  String? _error;
  String _userName = 'مستخدم';
  int _unreadNotifications = 0;

  // KPIs
  Decimal _totalRevenue = Decimal.zero;
  Decimal _totalExpenses = Decimal.zero;
  Decimal _netProfit = Decimal.zero;
  Decimal _totalAssets = Decimal.zero;
  Decimal _totalLiabilities = Decimal.zero;
  Decimal _totalEquity = Decimal.zero;
  Decimal _cashFlow = Decimal.zero;

  // Trends
  double _assetsTrend = 0;
  double _liabilitiesTrend = 0;
  double _equityTrend = 0;
  double _cashFlowTrend = 0;

  // Data
  List<MonthlyChartData> _monthlyData = [];
  List<RecentEntryModel> _recentEntries = [];
  List<AlertModel> _alerts = [];

  // ==================== Getters ====================
  bool get isLoading => _isLoading;
  String? get error => _error;
  String get userName => _userName;
  int get unreadNotifications => _unreadNotifications;

  Decimal get totalRevenue => _totalRevenue;
  Decimal get totalExpenses => _totalExpenses;
  Decimal get netProfit => _netProfit;
  Decimal get totalAssets => _totalAssets;
  Decimal get totalLiabilities => _totalLiabilities;
  Decimal get totalEquity => _totalEquity;
  Decimal get cashFlow => _cashFlow;

  double get assetsTrend => _assetsTrend;
  double get liabilitiesTrend => _liabilitiesTrend;
  double get equityTrend => _equityTrend;
  double get cashFlowTrend => _cashFlowTrend;

  List<MonthlyChartData> get monthlyData => _monthlyData;
  List<RecentEntryModel> get recentEntries => _recentEntries;
  List<AlertModel> get alerts => _alerts;

  double get maxChartValue {
    if (_monthlyData.isEmpty) return 100;
    var maxVal = Decimal.zero;
    for (var data in _monthlyData) {
      if (data.revenue > maxVal) maxVal = data.revenue;
      if (data.expenses > maxVal) maxVal = data.expenses;
    }
    return (maxVal * Decimal.fromInt(12) / Decimal.fromInt(10)).toDouble();
  }

  // ==================== Methods ====================
  Future<void> loadDashboardData() async {
    _setLoading(true);
    _error = null;

    try {
      // تحميل جميع البيانات بالتوازي
      final results = await Future.wait([
        _repository.getKpiSummary(),
        _repository.getMonthlyChart(6),
        _repository.getRecentEntries(5),
        _repository.getAlerts(),
        _repository.getUserInfo(),
      ]);

      final kpiData = results[0] as Map<String, dynamic>;
      _totalRevenue = parseMoney(kpiData['total_revenue']) ?? Decimal.zero;
      _totalExpenses = parseMoney(kpiData['total_expenses']) ?? Decimal.zero;
      _netProfit = parseMoney(kpiData['net_profit']) ?? Decimal.zero;
      _totalAssets = parseMoney(kpiData['total_assets']) ?? Decimal.zero;
      _totalLiabilities = parseMoney(kpiData['total_liabilities']) ?? Decimal.zero;
      _totalEquity = parseMoney(kpiData['total_equity']) ?? Decimal.zero;
      _cashFlow = parseMoney(kpiData['cash_flow']) ?? Decimal.zero;

      _assetsTrend = (kpiData['assets_trend'] ?? 0).toDouble();
      _liabilitiesTrend = (kpiData['liabilities_trend'] ?? 0).toDouble();
      _equityTrend = (kpiData['equity_trend'] ?? 0).toDouble();
      _cashFlowTrend = (kpiData['cash_flow_trend'] ?? 0).toDouble();

      _monthlyData = results[1] as List<MonthlyChartData>;
      _recentEntries = results[2] as List<RecentEntryModel>;
      _alerts = results[3] as List<AlertModel>;

      final userInfo = results[4] as Map<String, dynamic>;
      _userName = userInfo['name'] ?? 'مستخدم';
      _unreadNotifications = userInfo['unread_notifications'] ?? 0;
    } catch (e) {
      _error = 'فشل تحميل بيانات لوحة التحكم: $e';
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }
}