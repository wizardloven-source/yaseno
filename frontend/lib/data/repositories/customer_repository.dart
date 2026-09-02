import '../models/customer_model.dart';
import '../../services/api_service.dart';

class CustomerRepository {
  static List<Customer> _extractCustomers(dynamic response) {
    if (response is List) {
      return response.map((json) => Customer.fromJson(json as Map<String, dynamic>)).toList();
    }
    final items = response is Map ? (response['items'] ?? response['data'] ?? []) : [];
    if (items is List) {
      return items.map((json) => Customer.fromJson(json as Map<String, dynamic>)).toList();
    }
    return [];
  }

  static Customer? _extractCustomer(dynamic response) {
    if (response is Map) {
      if (response.containsKey('success') || response.containsKey('data') || response.containsKey('items')) {
        final d = response['data'] ?? response['items'];
        if (d is Map) {
          return Customer.fromJson(Map<String, dynamic>.from(d));
        }
      } else if (response.containsKey('id') || response.containsKey('name') || response.containsKey('code')) {
        return Customer.fromJson(Map<String, dynamic>.from(response));
      }
    }
    return null;
  }

  static bool _isSuccess(dynamic response) {
    if (response is Map && response.containsKey('success')) {
      return response['success'] == true;
    }
    return response != null;
  }

  // جلب جميع العملاء
  static Future<List<Customer>> getCustomers({
    String? status,
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final response = await ApiService.staticGet(
        'customers?limit=$limit&offset=$offset${status != null ? '&status=$status' : ''}'
      );
      return _extractCustomers(response);
    } catch (e) {
      print('Error fetching customers: $e');
      return [];
    }
  }

  // جلب عميل بالمعرف
  static Future<Customer?> getCustomer(String id) async {
    try {
      final response = await ApiService.staticGet('customers/$id');
      return _extractCustomer(response);
    } catch (e) {
      print('Error fetching customer: $e');
      return null;
    }
  }

  // إنشاء عميل جديد
  static Future<Customer?> createCustomer(Customer customer) async {
    try {
      final response = await ApiService.staticPost(
        'customers',
        data: customer.toJson(),
      );
      return _extractCustomer(response);
    } catch (e) {
      print('Error creating customer: $e');
      return null;
    }
  }

  // تحديث عميل
  static Future<Customer?> updateCustomer(Customer customer) async {
    try {
      final response = await ApiService.staticPut(
        'customers/${customer.id}',
        data: customer.toUpdateJson(),
      );
      return _extractCustomer(response);
    } catch (e) {
      print('Error updating customer: $e');
      return null;
    }
  }

  // حذف عميل
  static Future<bool> deleteCustomer(String id) async {
    try {
      final response = await ApiService.staticDelete('customers/$id');
      return _isSuccess(response);
    } catch (e) {
      print('Error deleting customer: $e');
      return false;
    }
  }

  // تغيير حالة العميل
  static Future<bool> changeStatus(String id, String newStatus) async {
    try {
      final response = await ApiService.staticPost(
        'customers/$id/status',
        data: {'status': newStatus},
      );
      return _isSuccess(response);
    } catch (e) {
      print('Error changing customer status: $e');
      return false;
    }
  }
}
