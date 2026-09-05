import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../domain/entities/fund.dart';
import '../../services/api_service.dart';
import '../../utils/error_utils.dart';

class FundsProvider extends ChangeNotifier {
  final ApiService _apiService = ApiService();

  List<Fund> _funds = [];
  Fund? _selectedFund;
  bool _isLoading = false;
  String? _error;

  List<Fund> get funds => _funds;
  Fund? get selectedFund => _selectedFund;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadFunds({String? type, bool includeInactive = false}) async {
    _setLoading(true);
    try {
      final response = await _apiService.get('/funds', queryParameters: {
        'include_inactive': includeInactive,
        if (type != null) 'fund_type': type,
      });
      final items = response['items'] ?? response['funds'] ?? [];
      _funds = (items is List ? items : [])
          .map((e) => Fund.fromJson(e as Map<String, dynamic>))
          .toList();
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      _funds = [];
    } finally {
      _setLoading(false);
    }
  }

  Future<Fund> getFund(String id) async {
    try {
      final response = await _apiService.get('/funds/$id');
      return Fund.fromJson(response);
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    }
  }

  Future<Fund> createFund({
    required String code,
    required String name,
    required String accountCode,
    String fundType = 'main',
    String currency = 'USD',
    String createdBy = 'system',
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.post('/funds', data: {
        'code': code,
        'name': name,
        'account_code': accountCode,
        'fund_type': fundType,
        'currency': currency,
        'created_by': createdBy,
      });
      final fund = Fund.fromJson(response);
      _funds.insert(0, fund);
      _error = null;
      return fund;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<Fund> updateFund({
    required String fundId,
    String? name,
    String? accountCode,
    String? currency,
    Decimal? dailyLimit,
    Decimal? monthlyLimit,
    Decimal? minBalanceAlert,
    Decimal? maxBalanceAlert,
    bool? requiresApproval,
    Decimal? approvalThreshold,
    String updatedBy = 'system',
    int version = 1,
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.put('/funds/$fundId', data: {
        if (name != null) 'name': name,
        if (accountCode != null) 'account_code': accountCode,
        if (currency != null) 'currency': currency,
        if (dailyLimit != null) 'daily_limit': dailyLimit.toString(),
        if (monthlyLimit != null) 'monthly_limit': monthlyLimit.toString(),
        if (minBalanceAlert != null) 'min_balance_alert': minBalanceAlert.toString(),
        if (maxBalanceAlert != null) 'max_balance_alert': maxBalanceAlert.toString(),
        if (requiresApproval != null) 'requires_approval': requiresApproval,
        if (approvalThreshold != null) 'approval_threshold': approvalThreshold.toString(),
        'updated_by': updatedBy,
        'version': version,
      });
      final fund = Fund.fromJson(response);
      final index = _funds.indexWhere((f) => f.id == fundId);
      if (index != -1) {
        _funds[index] = fund;
      }
      _error = null;
      return fund;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<Fund> depositToFund({
    required String fundId,
    required Decimal amount,
    required String reason,
    String? currency,
    String? referenceId,
    String createdBy = 'system',
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.depositToFund(fundId, {
        'amount': amount.toString(),
        'reason': reason,
        if (currency != null) 'currency': currency,
        if (referenceId != null) 'reference_id': referenceId,
        'created_by': createdBy,
      });
      final fund = Fund.fromJson(response);
      final index = _funds.indexWhere((f) => f.id == fundId);
      if (index != -1) {
        _funds[index] = fund;
      }
      _error = null;
      return fund;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<Fund> withdrawFromFund({
    required String fundId,
    required Decimal amount,
    required String reason,
    String? currency,
    String? referenceId,
    String createdBy = 'system',
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.withdrawFromFund(fundId, {
        'amount': amount.toString(),
        'reason': reason,
        if (currency != null) 'currency': currency,
        if (referenceId != null) 'reference_id': referenceId,
        'created_by': createdBy,
      });
      final fund = Fund.fromJson(response);
      final index = _funds.indexWhere((f) => f.id == fundId);
      if (index != -1) {
        _funds[index] = fund;
      }
      _error = null;
      return fund;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> transferBetweenFunds({
    required String fromFundId,
    required String toFundId,
    required Decimal amount,
    required String reason,
    String createdBy = 'system',
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.transferFunds({
        'from_fund_id': fromFundId,
        'to_fund_id': toFundId,
        'amount': amount.toString(),
        'reason': reason,
        'created_by': createdBy,
      });
      final fromFundData = response['from_fund'];
      final toFundData = response['to_fund'];
      if (fromFundData != null) {
        final fromFund = Fund.fromJson(fromFundData);
        final fromIndex = _funds.indexWhere((f) => f.id == fromFundId);
        if (fromIndex != -1) _funds[fromIndex] = fromFund;
      }
      if (toFundData != null) {
        final toFund = Fund.fromJson(toFundData);
        final toIndex = _funds.indexWhere((f) => f.id == toFundId);
        if (toIndex != -1) _funds[toIndex] = toFund;
      }
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> deleteFund(String fundId, {bool permanent = false}) async {
    _setLoading(true);
    try {
      await _apiService.delete('/funds/$fundId');
      _funds.removeWhere((f) => f.id == fundId);
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Map<String, dynamic> getStatistics() {
    final total = _funds.length;
    final active = _funds.where((f) => f.isActive).length;
    final totalBalance = _funds.fold(Decimal.zero, (sum, f) => sum + f.balance);
    
    return {
      'total': total,
      'active': active,
      'inactive': total - active,
      'totalBalance': totalBalance,
    };
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void setSelectedFund(Fund? fund) {
    _selectedFund = fund;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
