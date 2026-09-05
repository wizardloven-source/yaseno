// lib/services/api_client.dart
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:async';
import 'dart:convert';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  
  late Dio _dio;
  final Logger _logger = Logger();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  
  static const String _envBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api',
  );

  String _baseUrl = _envBaseUrl;
  String? _accessToken;
  String? _refreshToken;
  Completer<void>? _refreshMutex;
  
  ApiClient._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));
    
    // Interceptor لإضافة Token
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (_accessToken != null) {
            options.headers['Authorization'] = 'Bearer $_accessToken';
          }
          return handler.next(options);
        },
        onResponse: (response, handler) {
          if (response.data is Map && response.data['success'] == false) {
            final msg = response.data['message'] ?? 'Request failed';
            final errors = response.data['errors'];
            final detail = errors is List && errors.isNotEmpty ? ': ${errors.join(", ")}' : '';
            return handler.reject(DioException(
              requestOptions: response.requestOptions,
              response: response,
              type: DioExceptionType.badResponse,
              message: '$msg$detail',
            ));
          }
          return handler.next(response);
        },
        onError: (DioException e, handler) async {
          if (e.response?.statusCode == 401 && !e.requestOptions.path.contains('/auth/')) {
            // محاولة تحديث Token مع mutex لمنع التحديث المتزامن
            if (_refreshMutex != null) {
              try {
                await _refreshMutex!.future;
                final options = e.requestOptions;
                options.headers['Authorization'] = 'Bearer $_accessToken';
                final retryResponse = await _dio.fetch(options);
                return handler.resolve(retryResponse);
              } catch (err) {
                return handler.next(e);
              }
            }
            _refreshMutex = Completer<void>();
            try {
              await _refreshTokenCall();
              _refreshMutex!.complete();
              _refreshMutex = null;
              final options = e.requestOptions;
              options.headers['Authorization'] = 'Bearer $_accessToken';
              final retryResponse = await _dio.fetch(options);
              return handler.resolve(retryResponse);
            } catch (err) {
              _refreshMutex!.completeError(err);
              _refreshMutex = null;
              await logout();
              return handler.next(e);
            }
          }
          return handler.next(e);
        },
      ),
    );
  }
  
  Future<void> init() async {
    await _loadTokens();
  }
  
  Future<void> _loadTokens() async {
    _accessToken = await _storage.read(key: 'access_token');
    _refreshToken = await _storage.read(key: 'refresh_token');
  }
  
  Future<void> _saveTokens(String accessToken, String refreshToken) async {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
    await _storage.write(key: 'access_token', value: accessToken);
    await _storage.write(key: 'refresh_token', value: refreshToken);
  }
  
  // =========================================================================
  // Authentication
  // =========================================================================
  
  Future<Map<String, dynamic>> login(String username, String password, {bool rememberMe = false}) async {
    try {
      final response = await _dio.post('/auth/login', data: {
        'username': username,
        'password': password,
        'remember_me': rememberMe,
      });
      
      if (response.statusCode == 200 && response.data['access_token'] != null) {
        await _saveTokens(
          response.data['access_token'],
          response.data['refresh_token'],
        );
        
        return {
          'success': true,
          'user': response.data['user'],
          'message': 'تم تسجيل الدخول بنجاح',
        };
      } else {
        throw Exception(response.data['detail'] ?? 'فشل تسجيل الدخول');
      }
    } on DioException catch (e) {
      throw Exception(e.response?.data['detail'] ?? 'خطأ في الاتصال بالخادم');
    }
  }
  
  Future<void> logout() async {
    try {
      if (_accessToken != null) {
        await _dio.post('/auth/logout');
      }
    } catch (e) {
      _logger.e('Logout error: $e');
    } finally {
      _accessToken = null;
      _refreshToken = null;
      await _storage.delete(key: 'access_token');
      await _storage.delete(key: 'refresh_token');
    }
  }
  
  Future<void> _refreshTokenCall() async {
    if (_refreshToken == null) {
      throw Exception('No refresh token available');
    }
    
    try {
      final response = await _dio.post('/auth/refresh', data: {
        'token': _refreshToken,
      });
      
      if (response.statusCode == 200 && response.data['access_token'] != null) {
        _accessToken = response.data['access_token'];
        _refreshToken = response.data['refresh_token'];
        await _storage.write(key: 'access_token', value: _accessToken);
        await _storage.write(key: 'refresh_token', value: _refreshToken);
      } else {
        throw Exception('Failed to refresh token');
      }
    } on DioException {
      await logout();
      throw Exception('Session expired');
    }
  }
  
  Future<Map<String, dynamic>?> getCurrentUser() async {
    try {
      final response = await _dio.get('/auth/me');
      return response.data;
    } on DioException {
      return null;
    }
  }
  
  Future<void> changePassword(String oldPassword, String newPassword) async {
    try {
      await _dio.post('/auth/change-password', data: {
        'old_password': oldPassword,
        'new_password': newPassword,
      });
    } on DioException catch (e) {
      throw Exception(e.response?.data['detail'] ?? 'فشل تغيير كلمة المرور');
    }
  }
  
  bool get isAuthenticated => _accessToken != null;
  
  Dio get dio => _dio;
  
  // =========================================================================
  // Journal Entries
  // =========================================================================
  
  Future<Map<String, dynamic>> getJournalEntries({
    int limit = 100,
    int offset = 0,
    bool? isPosted,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    try {
      final queryParams = {
        'limit': limit,
        'offset': offset,
        if (isPosted != null) 'is_posted': isPosted,
        if (fromDate != null) 'from_date': fromDate.toIso8601String().split('T')[0],
        if (toDate != null) 'to_date': toDate.toIso8601String().split('T')[0],
      };
      
      final response = await _dio.get('/journal-entries', queryParameters: queryParams);
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب القيود');
    }
  }
  
  Future<Map<String, dynamic>> getJournalEntry(String entryId) async {
    try {
      final response = await _dio.get('/journal-entries/$entryId');
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب القيد');
    }
  }
  
  Future<Map<String, dynamic>> createJournalEntry({
    required DateTime date,
    required String description,
    required List<Map<String, dynamic>> lines,
    String? transactionType,
    String? notes,
  }) async {
    try {
      final response = await _dio.post('/journal-entries', data: {
        'date': date.toIso8601String().split('T')[0],
        'description': description,
        'lines': lines,
        if (transactionType != null) 'transaction_type': transactionType,
        if (notes != null) 'notes': notes,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل إنشاء القيد');
    }
  }
  
  Future<Map<String, dynamic>> postJournalEntry(String entryId) async {
    try {
      final response = await _dio.post('/journal-entries/$entryId/post');
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل ترحيل القيد');
    }
  }
  
  Future<Map<String, dynamic>> reverseJournalEntry(String entryId, String reason) async {
    try {
      final response = await _dio.post(
        '/journal-entries/$entryId/reverse',
        queryParameters: {'reason': reason},
      );
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل عكس القيد');
    }
  }
  
  // =========================================================================
  // Accounts
  // =========================================================================
  
  Future<List<Map<String, dynamic>>> getAccounts({
    String? accountType,
    bool includeInactive = false,
  }) async {
    try {
      final response = await _dio.get('/accounts', queryParameters: {
        if (accountType != null) 'account_type': accountType,
        'include_inactive': includeInactive,
      });
      
      return List<Map<String, dynamic>>.from(response.data['data']?['accounts'] ?? []);
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب الحسابات');
    }
  }
  
  Future<Map<String, dynamic>> createAccount({
    required String code,
    required String name,
    required String accountType,
    String? parentCode,
    String? description,
    String currency = 'USD',
    bool isActive = true,
  }) async {
    try {
      final response = await _dio.post('/accounts', data: {
        'code': code,
        'name': name,
        'account_type': accountType,
        if (parentCode != null) 'parent_code': parentCode,
        if (description != null) 'description': description,
        'currency': currency,
        'is_active': isActive,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل إنشاء الحساب');
    }
  }
  
  // =========================================================================
  // Customers
  // =========================================================================
  
  Future<Map<String, dynamic>> getCustomers({
    int limit = 100,
    int offset = 0,
    String? status,
  }) async {
    try {
      final response = await _dio.get('/customers', queryParameters: {
        'limit': limit,
        'offset': offset,
        if (status != null) 'status': status,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب العملاء');
    }
  }
  
  Future<Map<String, dynamic>> createCustomer({
    required String code,
    required String name,
    String? email,
    String? phone,
    String? mobile,
    String? street,
    String? city,
    String country = 'LB',
    String? taxNumber,
    double creditLimit = 0,
    String currency = 'USD',
    String? notes,
  }) async {
    try {
      final response = await _dio.post('/customers', data: {
        'code': code,
        'name': name,
        if (email != null) 'email': email,
        if (phone != null) 'phone': phone,
        if (mobile != null) 'mobile': mobile,
        if (street != null) 'street': street,
        if (city != null) 'city': city,
        'country': country,
        if (taxNumber != null) 'tax_number': taxNumber,
        'credit_limit': creditLimit,
        'currency': currency,
        if (notes != null) 'notes': notes,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل إنشاء العميل');
    }
  }
  
  // =========================================================================
  // Invoices
  // =========================================================================
  
  Future<Map<String, dynamic>> getInvoices({
    int limit = 100,
    int offset = 0,
    String? status,
  }) async {
    try {
      final response = await _dio.get('/invoices', queryParameters: {
        'limit': limit,
        'offset': offset,
        if (status != null) 'status': status,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب الفواتير');
    }
  }
  
  Future<Map<String, dynamic>> createInvoice({
    required String customerId,
    required String customerName,
    String currency = 'USD',
    String paymentType = 'cash',
    String? siteId,
    String? siteName,
    required List<Map<String, dynamic>> lines,
    String? notes,
  }) async {
    try {
      final response = await _dio.post('/invoices', data: {
        'customer_id': customerId,
        'customer_name': customerName,
        'currency': currency,
        'payment_type': paymentType,
        if (siteId != null) 'site_id': siteId,
        if (siteName != null) 'site_name': siteName,
        'lines': lines,
        if (notes != null) 'notes': notes,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل إنشاء الفاتورة');
    }
  }
  
  // =========================================================================
  // Payments
  // =========================================================================
  
  Future<Map<String, dynamic>> getPayments({
    int limit = 100,
    int offset = 0,
    String? status,
    String? paymentMethod,
  }) async {
    try {
      final response = await _dio.get('/payments', queryParameters: {
        'limit': limit,
        'offset': offset,
        if (status != null) 'status': status,
        if (paymentMethod != null) 'payment_method': paymentMethod,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب الدفعات');
    }
  }
  
  Future<Map<String, dynamic>> createPayment({
    required String paymentType,
    required String paymentMethod,
    required double amount,
    String currency = 'USD',
    required String fundId,
    String? customerId,
    String? supplierId,
    String? invoiceId,
    String? description,
    DateTime? dueDate,
  }) async {
    try {
      final response = await _dio.post('/payments', data: {
        'payment_type': paymentType,
        'payment_method': paymentMethod,
        'amount': amount,
        'currency': currency,
        'fund_id': fundId,
        if (customerId != null) 'customer_id': customerId,
        if (supplierId != null) 'supplier_id': supplierId,
        if (invoiceId != null) 'invoice_id': invoiceId,
        if (description != null) 'description': description,
        if (dueDate != null) 'due_date': dueDate.toIso8601String().split('T')[0],
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل إنشاء الدفعة');
    }
  }
  
  Future<Map<String, dynamic>> completePayment(String paymentId) async {
    try {
      final response = await _dio.post('/payments/$paymentId/complete');
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل إكمال الدفعة');
    }
  }
  
  // =========================================================================
  // Funds
  // =========================================================================
  
  Future<Map<String, dynamic>> getFunds({
    int limit = 100,
    int offset = 0,
    bool includeInactive = false,
  }) async {
    try {
      final response = await _dio.get('/funds', queryParameters: {
        'limit': limit,
        'offset': offset,
        'include_inactive': includeInactive,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب الصناديق');
    }
  }
  
  // =========================================================================
  // Products
  // =========================================================================
  
  Future<Map<String, dynamic>> getProducts({
    int limit = 100,
    int offset = 0,
    bool includeInactive = false,
    String? category,
  }) async {
    try {
      final response = await _dio.get('/products', queryParameters: {
        'limit': limit,
        'offset': offset,
        'include_inactive': includeInactive,
        if (category != null) 'category': category,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب المنتجات');
    }
  }
  
  // =========================================================================
  // Suppliers
  // =========================================================================
  
  Future<Map<String, dynamic>> getSuppliers({
    int limit = 100,
    int offset = 0,
    String? status,
  }) async {
    try {
      final response = await _dio.get('/suppliers', queryParameters: {
        'limit': limit,
        'offset': offset,
        if (status != null) 'status': status,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب الموردين');
    }
  }
  
  // =========================================================================
  // Purchase Orders
  // =========================================================================
  
  Future<Map<String, dynamic>> getPurchaseOrders({
    int limit = 100,
    int offset = 0,
    String? status,
  }) async {
    try {
      final response = await _dio.get('/purchase-orders', queryParameters: {
        'limit': limit,
        'offset': offset,
        if (status != null) 'status': status,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل جلب أوامر الشراء');
    }
  }
  
  // =========================================================================
  // Reports
  // =========================================================================
  
  Future<Map<String, dynamic>> getTrialBalance({
    required DateTime asOfDate,
    bool includeZeroBalance = false,
    String currency = 'USD',
  }) async {
    try {
      final response = await _dio.get('/reports/trial-balance', queryParameters: {
        'as_of_date': asOfDate.toIso8601String().split('T')[0],
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل توليد ميزان المراجعة');
    }
  }
  
  Future<Map<String, dynamic>> getIncomeStatement({
    required DateTime startDate,
    required DateTime endDate,
    String currency = 'USD',
  }) async {
    try {
      final response = await _dio.post('/reports/income-statement', data: {
        'period_start': startDate.toIso8601String().split('T')[0],
        'period_end': endDate.toIso8601String().split('T')[0],
        'currency': currency,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل توليد قائمة الدخل');
    }
  }
  
  Future<Map<String, dynamic>> getBalanceSheet({
    required DateTime asOfDate,
    String currency = 'USD',
  }) async {
    try {
      final response = await _dio.post('/reports/balance-sheet', data: {
        'as_of_date': asOfDate.toIso8601String().split('T')[0],
        'currency': currency,
      });
      
      return response.data;
    } on DioException catch (e) {
      throw Exception(e.response?.data['message'] ?? 'فشل توليد الميزانية العمومية');
    }
  }
  
  // =========================================================================
  // Health Check
  // =========================================================================
  
  Future<bool> checkHealth() async {
    try {
      final response = await _dio.get('/health');
      return response.statusCode == 200 && response.data['success'] == true;
    } catch (e) {
      return false;
    }
  }
  
  Future<bool> checkDatabaseHealth() async {
    try {
      final response = await _dio.get('/health/db');
      return response.statusCode == 200 && response.data['success'] == true;
    } catch (e) {
      return false;
    }
  }
}