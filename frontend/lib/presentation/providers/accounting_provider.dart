import 'package:flutter/foundation.dart';
import 'package:decimal/decimal.dart';
import '../../services/api_service.dart';
import '../../data/models/accounting/account.dart';
import '../../domain/entities/journal_entry.dart';
import '../../utils/error_utils.dart';

class AccountingProvider extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  
  List<JournalEntry> _journalEntries = [];
  List<Account> _accounts = [];
  List<JournalEntry> _recentEntries = [];
  
  bool _isLoading = false;
  String? _error;
  JournalEntry? _selectedEntry;

  List<JournalEntry> get journalEntries => _journalEntries;
  List<Account> get accounts => _accounts;
  List<JournalEntry> get recentEntries => _recentEntries;
  bool get isLoading => _isLoading;
  String? get error => _error;
  JournalEntry? get selectedEntry => _selectedEntry;

  int get totalEntries => _journalEntries.length;
  int get postedEntries => _journalEntries.where((e) => e.isPosted).length;
  int get draftEntries => _journalEntries.where((e) => !e.isPosted).length;
  Decimal get totalDebit => _journalEntries.fold(Decimal.zero, (sum, e) => sum + e.totalDebit);
  Decimal get totalCredit => _journalEntries.fold(Decimal.zero, (sum, e) => sum + e.totalCredit);

  Future<void> loadJournalEntries({
    int limit = 100,
    int offset = 0,
    bool? isPosted,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    _setLoading(true);
    
    try {
      final query = <String, dynamic>{
        'limit': limit,
        'offset': offset,
        if (isPosted != null) 'is_posted': isPosted,
        if (fromDate != null) 'from_date': fromDate.toIso8601String().split('T')[0],
        if (toDate != null) 'to_date': toDate.toIso8601String().split('T')[0],
      };
      
      _journalEntries = await _apiService.getJournalEntries(query);
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
    } finally {
      _setLoading(false);
    }
  }

  Future<JournalEntry?> getJournalEntry(String entryId) async {
    try {
      final response = await _apiService.get('/journal-entries/$entryId');
      return JournalEntry.fromJson(response);
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      return null;
    }
  }

  Future<bool> createJournalEntry({
    required DateTime date,
    required String description,
    required List<Map<String, dynamic>> lines,
    String? transactionType,
    String? notes,
  }) async {
    _setLoading(true);
    
    try {
      await _apiService.post('/journal-entries', data: {
        'date': date.toIso8601String().split('T')[0],
        'description': description,
        'lines': lines,
        if (transactionType != null) 'transaction_type': transactionType,
        if (notes != null) 'notes': notes,
      });
      
      await loadJournalEntries();
      return true;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      return false;
    } finally {
      _setLoading(false);
    }
  }

  Future<bool> postJournalEntry(String entryId) async {
    _setLoading(true);
    
    try {
      await _apiService.post('/journal-entries/$entryId/post');
      await loadJournalEntries();
      return true;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      return false;
    } finally {
      _setLoading(false);
    }
  }

  Future<bool> reverseJournalEntry(String entryId, String reason) async {
    _setLoading(true);
    
    try {
      await _apiService.post(
        '/journal-entries/$entryId/reverse',
        data: {'reason': reason},
      );
      await loadJournalEntries();
      return true;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      return false;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> loadAccounts({
    String? accountType,
    bool includeInactive = false,
  }) async {
    _setLoading(true);
    
    try {
      final response = await _apiService.get('/accounts', queryParameters: {
        if (accountType != null) 'account_type': accountType,
        'include_inactive': includeInactive,
      });
      
      final accountsList = response['accounts'] ?? response['items'] ?? [];
      _accounts = (accountsList as List)
          .map((item) => Account.fromJson(item as Map<String, dynamic>))
          .toList();
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
    } finally {
      _setLoading(false);
    }
  }

  Future<bool> createAccount({
    required String code,
    required String name,
    required String accountType,
    String? parentCode,
    String? description,
  }) async {
    _setLoading(true);
    
    try {
      await _apiService.post('/accounts', data: {
        'code': code,
        'name': name,
        'account_type': accountType,
        if (parentCode != null) 'parent_code': parentCode,
        if (description != null) 'description': description,
      });
      
      await loadAccounts();
      return true;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      return false;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> loadDashboardData() async {
    await Future.wait([
      loadJournalEntries(limit: 10),
      loadAccounts(),
    ]);
    
    _recentEntries = _journalEntries.take(5).toList();
    notifyListeners();
  }

  Future<Map<String, dynamic>?> getTrialBalance({
    required DateTime asOfDate,
    bool includeZeroBalance = false,
  }) async {
    _setLoading(true);
    
    try {
      final response = await _apiService.post('/reports/trial-balance', data: {
        'as_of_date': asOfDate.toIso8601String().split('T')[0],
        'include_zero_balance': includeZeroBalance,
      });
      return response;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      return null;
    } finally {
      _setLoading(false);
    }
  }

  Future<Map<String, dynamic>?> getIncomeStatement({
    required DateTime startDate,
    required DateTime endDate,
  }) async {
    _setLoading(true);
    
    try {
      final response = await _apiService.post('/reports/income-statement', data: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
      });
      return response;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      return null;
    } finally {
      _setLoading(false);
    }
  }

  void setSelectedEntry(JournalEntry? entry) {
    _selectedEntry = entry;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
}
