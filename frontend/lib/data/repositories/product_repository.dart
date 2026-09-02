import '../models/product_model.dart';
import '../../services/api_service.dart';

class ProductRepository {
  static List<Product> _extractProducts(dynamic response) {
    if (response is List) {
      return response.map((json) => Product.fromJson(json as Map<String, dynamic>)).toList();
    }
    final items = response is Map ? (response['data'] ?? response['items'] ?? []) : [];
    if (items is List) {
      return items.map((json) => Product.fromJson(json as Map<String, dynamic>)).toList();
    }
    return [];
  }

  static Product? _extractProduct(dynamic response) {
    if (response is Map) {
      if (response.containsKey('success') || response.containsKey('data') || response.containsKey('items')) {
        final d = response['data'] ?? response['items'];
        if (d is Map) {
          return Product.fromJson(Map<String, dynamic>.from(d));
        }
      } else if (response.containsKey('id') || response.containsKey('name')) {
        return Product.fromJson(Map<String, dynamic>.from(response));
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

  static Future<List<Product>> getProducts({
    bool includeInactive = false,
    String? category,
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final response = await ApiService.staticGet(
        'products?limit=$limit&offset=$offset&include_inactive=$includeInactive${category != null ? '&category=$category' : ''}'
      );
      return _extractProducts(response);
    } catch (e) {
      print('Error fetching products: $e');
      return [];
    }
  }

  static Future<Product?> getProduct(String id) async {
    try {
      final response = await ApiService.staticGet('products/$id');
      return _extractProduct(response);
    } catch (e) {
      print('Error fetching product: $e');
      return null;
    }
  }

  static Future<List<Product>> getLowStockProducts({int threshold = 10}) async {
    try {
      final response = await ApiService.staticGet('products/low-stock?threshold=$threshold');
      return _extractProducts(response);
    } catch (e) {
      print('Error fetching low stock products: $e');
      return [];
    }
  }

  static Future<Product?> createProduct(Product product) async {
    try {
      final response = await ApiService.staticPost(
        'products',
        data: product.toJson(),
      );
      return _extractProduct(response);
    } catch (e) {
      print('Error creating product: $e');
      return null;
    }
  }

  static Future<Product?> updateProduct(Product product) async {
    try {
      final response = await ApiService.staticPut(
        'products/${product.id}',
        data: product.toUpdateJson(),
      );
      return _extractProduct(response);
    } catch (e) {
      print('Error updating product: $e');
      return null;
    }
  }

  static Future<bool> deleteProduct(String id) async {
    try {
      final response = await ApiService.staticDelete('products/$id');
      return _isSuccess(response);
    } catch (e) {
      print('Error deleting product: $e');
      return false;
    }
  }

  static Future<Product?> updateStock(String productId, int quantityChange, String reason) async {
    try {
      final response = await ApiService.staticPut(
        'products/$productId/stock',
        data: {
          'quantityChange': quantityChange,
          'reason': reason,
        },
      );
      return _extractProduct(response);
    } catch (e) {
      print('Error updating stock: $e');
      return null;
    }
  }
}
