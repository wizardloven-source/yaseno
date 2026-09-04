import 'api_client.dart';
import '../data/models/accounting/account.dart';
import '../domain/entities/journal_entry.dart';

class ApiService {
  static final ApiClient _client = ApiClient();
  static String? _cachedBaseCurrencyCode;
  static String? _cachedBaseCurrencySymbol;

  // =========================================================================
  // Static HTTP methods (used by repositories)
  // =========================================================================

  static Future<Map<String, dynamic>> staticGet(
    String endpoint, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final dio = ApiClient().dio;
    final response = await dio.get(
      '/$endpoint',
      queryParameters: queryParameters,
    );
    return _extractData(response.data);
  }

  static Future<Map<String, dynamic>> staticPost(
    String endpoint, {
    Map<String, dynamic>? data,
  }) async {
    final dio = ApiClient().dio;
    final response = await dio.post('/$endpoint', data: data);
    return _extractData(response.data);
  }

  static Future<Map<String, dynamic>> staticPut(
    String endpoint, {
    Map<String, dynamic>? data,
  }) async {
    final dio = ApiClient().dio;
    final response = await dio.put('/$endpoint', data: data);
    return _extractData(response.data);
  }

  static Future<Map<String, dynamic>> staticDelete(String endpoint) async {
    final dio = ApiClient().dio;
    final response = await dio.delete('/$endpoint');
    return _extractData(response.data);
  }

  static Map<String, dynamic> _extractData(dynamic responseData) {
    if (responseData is Map<String, dynamic>) {
      if (responseData.containsKey('data')) {
        return responseData['data'] is Map<String, dynamic>
            ? Map<String, dynamic>.from(responseData['data'])
            : responseData;
      }
      return responseData;
    }
    return {'data': responseData};
  }

  // =========================================================================
  // Instance HTTP methods (used by providers that instantiate ApiService)
  // =========================================================================

  Future<Map<String, dynamic>> get(
    String endpoint, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final dio = _client.dio;
    final response = await dio.get(
      endpoint.startsWith('/') ? endpoint : '/$endpoint',
      queryParameters: queryParameters,
    );
    return _extractData(response.data);
  }

  Future<Map<String, dynamic>> post(
    String endpoint, {
    Map<String, dynamic>? data,
  }) async {
    final dio = _client.dio;
    final response = await dio.post(
      endpoint.startsWith('/') ? endpoint : '/$endpoint',
      data: data,
    );
    return _extractData(response.data);
  }

  Future<Map<String, dynamic>> put(
    String endpoint, {
    Map<String, dynamic>? data,
  }) async {
    final dio = _client.dio;
    final response = await dio.put(
      endpoint.startsWith('/') ? endpoint : '/$endpoint',
      data: data,
    );
    return _extractData(response.data);
  }

  Future<Map<String, dynamic>> patch(
    String endpoint, {
    Map<String, dynamic>? data,
  }) async {
    final dio = _client.dio;
    final response = await dio.patch(
      endpoint.startsWith('/') ? endpoint : '/$endpoint',
      data: data,
    );
    return _extractData(response.data);
  }

  Future<Map<String, dynamic>> delete(String endpoint) async {
    final dio = _client.dio;
    final response = await dio.delete(
      endpoint.startsWith('/') ? endpoint : '/$endpoint',
    );
    return _extractData(response.data);
  }

  // =========================================================================
  // Accounting - Journal Entries
  // =========================================================================

  Future<List<JournalEntry>> getJournalEntries(
      [Map<String, dynamic>? query]) async {
    final response = await _client.dio.get(
      '/journal-entries',
      queryParameters: query,
    );
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items
          .map((e) => JournalEntry.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return [];
  }

  Future<JournalEntry> createJournalEntry({
    required DateTime date,
    required String description,
    required List<Map<String, dynamic>> lines,
    String? transactionType,
    String? createdBy,
  }) async {
    final response = await _client.dio.post('/journal-entries', data: {
      'date': date.toIso8601String().split('T')[0],
      'description': description,
      'lines': lines,
      if (transactionType != null) 'transaction_type': transactionType,
    });
    return JournalEntry.fromJson(response.data);
  }

  Future<JournalEntry> postJournalEntry(
      String entryId, String postedBy) async {
    final response =
        await _client.dio.post('/journal-entries/$entryId/post');
    return JournalEntry.fromJson(response.data);
  }

  Future<JournalEntry> reverseJournalEntry(
      String entryId, String reason, String reversedBy) async {
    final response = await _client.dio.post(
      '/journal-entries/$entryId/reverse',
      queryParameters: {'reason': reason},
    );
    return JournalEntry.fromJson(response.data);
  }

  // =========================================================================
  // Accounting - Accounts
  // =========================================================================

  Future<List<Account>> getAccounts() async {
    final response = await _client.dio.get('/accounts');
    final data = response.data;
    final accountsList = data['data']?['accounts'] ?? data['data'] ?? [];
    if (accountsList is List) {
      return accountsList
          .map((e) => Account.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return [];
  }

  // =========================================================================
  // Invoices
  // =========================================================================

  Future<Map<String, dynamic>> getInvoice(String invoiceId) async {
    final response = await _client.dio.get('/invoices/$invoiceId');
    return response.data;
  }

  Future<Map<String, dynamic>> postInvoice(String invoiceId,
      {bool force = false}) async {
    final response = await _client.dio.post('/invoices/$invoiceId/post',
        data: {'force': force});
    return response.data;
  }

  Future<Map<String, dynamic>> cancelInvoice(String invoiceId,
      {String? reason}) async {
    final response = await _client.dio.post('/invoices/$invoiceId/cancel',
        data: {'reason': reason});
    return response.data;
  }

  Future<Map<String, dynamic>> returnInvoice(String invoiceId,
      {required String reason}) async {
    final response = await _client.dio.post('/invoices/$invoiceId/return',
        data: {'reason': reason});
    return response.data;
  }

  // =========================================================================
  // Payments
  // =========================================================================

  Future<Map<String, dynamic>> getPayment(String paymentId) async {
    final response = await _client.dio.get('/payments/$paymentId');
    return response.data;
  }

  Future<Map<String, dynamic>> submitPayment(String paymentId) async {
    final response =
        await _client.dio.post('/payments/$paymentId/submit');
    return response.data;
  }

  Future<Map<String, dynamic>> approvePayment(String paymentId) async {
    final response =
        await _client.dio.post('/payments/$paymentId/approve');
    return response.data;
  }

  Future<Map<String, dynamic>> rejectPayment(String paymentId,
      {String? reason}) async {
    final response = await _client.dio.post('/payments/$paymentId/reject',
        data: {'reason': reason ?? ''});
    return response.data;
  }

  Future<Map<String, dynamic>> cancelPayment(String paymentId,
      {String? reason}) async {
    final response = await _client.dio.post('/payments/$paymentId/cancel',
        data: {'reason': reason ?? ''});
    return response.data;
  }

  Future<Map<String, dynamic>> deletePayment(String paymentId) async {
    final response = await _client.dio.delete('/payments/$paymentId');
    return response.data;
  }

  // =========================================================================
  // Funds
  // =========================================================================

  Future<Map<String, dynamic>> getFund(String fundId) async {
    final response = await _client.dio.get('/funds/$fundId');
    return response.data;
  }

  Future<Map<String, dynamic>> createFund(Map<String, dynamic> data) async {
    final response = await _client.dio.post('/funds', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> depositToFund(
      String fundId, Map<String, dynamic> data) async {
    final response =
        await _client.dio.post('/funds/$fundId/deposit', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> withdrawFromFund(
      String fundId, Map<String, dynamic> data) async {
    final response =
        await _client.dio.post('/funds/$fundId/withdraw', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> transferFunds(
      Map<String, dynamic> data) async {
    final response =
        await _client.dio.post('/funds/transfer', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> getFundBalance(String fundId) async {
    final response = await _client.dio.get('/funds/$fundId/balance');
    return response.data;
  }

  Future<List<Map<String, dynamic>>> getFundMovements(String fundId,
      {int limit = 100}) async {
    final response = await _client.dio.get(
      '/funds/$fundId/movements',
      queryParameters: {'limit': limit},
    );
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items.cast<Map<String, dynamic>>();
    }
    return [];
  }

  // =========================================================================
  // Purchase Orders
  // =========================================================================

  Future<Map<String, dynamic>> getPurchaseOrder(String orderId) async {
    final response = await _client.dio.get('/purchase-orders/$orderId');
    return response.data;
  }

  Future<Map<String, dynamic>> createPurchaseOrder(
      Map<String, dynamic> data) async {
    final response =
        await _client.dio.post('/purchase-orders', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> postPurchaseOrder(String orderId) async {
    final response =
        await _client.dio.post('/purchase-orders/$orderId/post');
    return response.data;
  }

  Future<Map<String, dynamic>> receivePurchaseOrder(String orderId,
      {Map<String, dynamic>? data}) async {
    final response = await _client.dio.post(
      '/purchase-orders/$orderId/receive',
      data: data,
    );
    return response.data;
  }

  Future<Map<String, dynamic>> returnPurchaseOrder(String orderId,
      {required String reason}) async {
    final response = await _client.dio.post(
      '/purchase-orders/$orderId/return',
      data: {'reason': reason},
    );
    return response.data;
  }

  // =========================================================================
  // Inventory
  // =========================================================================

  Future<Map<String, dynamic>> getStockQuantity(
      String entityType, String entityId) async {
    final response = await _client.dio
        .get('/inventory/$entityType/$entityId/quantity');
    return response.data;
  }

  Future<List<Map<String, dynamic>>> getStockMovements(
      String entityType, String entityId,
      {int limit = 100}) async {
    final response = await _client.dio.get(
      '/inventory/$entityType/$entityId/movements',
      queryParameters: {'limit': limit},
    );
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items.cast<Map<String, dynamic>>();
    }
    return [];
  }

  Future<Map<String, dynamic>> createStockMovement(
      Map<String, dynamic> data) async {
    final response =
        await _client.dio.post('/inventory/movements', data: data);
    return response.data;
  }

  // =========================================================================
  // Currencies
  // =========================================================================

  Future<List<Map<String, dynamic>>> getCurrencies() async {
    final response = await _client.dio.get('/currency');
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items.cast<Map<String, dynamic>>();
    }
    return [];
  }

  Future<Map<String, dynamic>> getExchangeRate(
      String fromCode, String toCode) async {
    final response = await _client.dio.get(
      '/currency/exchange-rate',
      queryParameters: {
        'from_currency_code': fromCode,
        'to_currency_code': toCode,
      },
    );
    return response.data;
  }

  // =========================================================================
  // Sites
  // =========================================================================

  Future<List<Map<String, dynamic>>> getSites() async {
    final response = await _client.dio.get('/sites');
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items.cast<Map<String, dynamic>>();
    }
    return [];
  }

  // =========================================================================
  // Cost Centers
  // =========================================================================

  Future<List<Map<String, dynamic>>> getCenters() async {
    final response = await _client.dio.get('/centers');
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items.cast<Map<String, dynamic>>();
    }
    return [];
  }

  // =========================================================================
  // Fixed Assets
  // =========================================================================

  Future<Map<String, dynamic>> getAssets({int limit = 100}) async {
    final response = await _client.dio
        .get('/assets', queryParameters: {'limit': limit});
    return response.data;
  }

  // =========================================================================
  // Workflows
  // =========================================================================

  Future<List<Map<String, dynamic>>> getWorkflows() async {
    final response = await _client.dio.get('/workflows');
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items.cast<Map<String, dynamic>>();
    }
    return [];
  }

  Future<List<Map<String, dynamic>>> getPendingApprovals() async {
    final response = await _client.dio.get('/approval-requests/pending');
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items.cast<Map<String, dynamic>>();
    }
    return [];
  }

  // =========================================================================
  // Reports
  // =========================================================================

  Future<Map<String, dynamic>> getTrialBalanceReport(
      DateTime asOfDate) async {
    final response = await _client.dio.get(
      '/reports/trial-balance',
      queryParameters: {'as_of_date': asOfDate.toIso8601String().split('T')[0]},
    );
    return response.data;
  }

  Future<Map<String, dynamic>> getIncomeStatementReport(
      DateTime startDate, DateTime endDate) async {
    final response = await _client.dio.post('/reports/income-statement',
        data: {
          'period_start': startDate.toIso8601String().split('T')[0],
          'period_end': endDate.toIso8601String().split('T')[0],
        });
    return response.data;
  }

  Future<Map<String, dynamic>> getBalanceSheetReport(
      DateTime asOfDate) async {
    final response = await _client.dio.post('/reports/balance-sheet',
        data: {
          'as_of_date': asOfDate.toIso8601String().split('T')[0],
        });
    return response.data;
  }

  Future<Map<String, dynamic>> getCashFlowReport(
      DateTime startDate, DateTime endDate) async {
    final response = await _client.dio.post('/reports/cash-flow',
        data: {
          'period_start': startDate.toIso8601String().split('T')[0],
          'period_end': endDate.toIso8601String().split('T')[0],
        });
    return response.data;
  }

  // =========================================================================
  // Settings
  // =========================================================================

  Future<Map<String, dynamic>> getSettings() async {
    final response = await _client.dio.get('/settings');
    return response.data;
  }

  Future<Map<String, dynamic>> updateSettings(
      Map<String, dynamic> data) async {
    final response = await _client.dio.put('/settings', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> getUiSettings() async {
    final response = await _client.dio.get('/settings/ui');
    return response.data;
  }

  Future<Map<String, dynamic>> updateUiSettings(
      Map<String, dynamic> data) async {
    final response = await _client.dio.put('/settings/ui', data: data);
    return response.data;
  }

  // =========================================================================
  // Users
  // =========================================================================

  Future<List<Map<String, dynamic>>> getUsers({int limit = 100}) async {
    final response = await _client.dio
        .get('/auth/users', queryParameters: {'limit': limit});
    final data = response.data;
    final items = data['data']?['items'] ?? data['data'] ?? [];
    if (items is List) {
      return items.cast<Map<String, dynamic>>();
    }
    return [];
  }

  Future<Map<String, dynamic>> getCurrentUser() async {
    final response = await _client.dio.get('/auth/me');
    return response.data;
  }

  // =========================================================================
  // Currency helpers (cached)
  // =========================================================================

  static Future<String> getBaseCurrencyCode() async {
    if (_cachedBaseCurrencyCode != null) return _cachedBaseCurrencyCode!;
    try {
      final response = await _client.dio.get('/currency/base');
      final data = response.data;
      final inner = data['data'];
      _cachedBaseCurrencyCode = (inner is Map ? inner['code'] : null) ?? 'IQD';
    } catch (_) {
      _cachedBaseCurrencyCode = 'IQD';
    }
    return _cachedBaseCurrencyCode!;
  }

  static Future<String> getBaseCurrencySymbol() async {
    if (_cachedBaseCurrencySymbol != null) return _cachedBaseCurrencySymbol!;
    try {
      final response = await _client.dio.get('/currency/base');
      final data = response.data;
      final inner = data['data'];
      _cachedBaseCurrencySymbol = (inner is Map ? inner['symbol'] : null) ?? 'د.ع';
    } catch (_) {
      _cachedBaseCurrencySymbol = 'د.ع';
    }
    return _cachedBaseCurrencySymbol!;
  }

  static void clearCurrencyCache() {
    _cachedBaseCurrencyCode = null;
    _cachedBaseCurrencySymbol = null;
  }
}
