import '../models/supplier_model.dart';
import '../../services/api_service.dart';
import '../../utils/error_logger.dart';

class SupplierRepository {
  static Future<List<Supplier>> getSuppliers({
    String? status,
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final response = await ApiService.staticGet(
        'suppliers?limit=$limit&offset=$offset${status != null ? '&status=$status' : ''}'
      );
      final data = response['items'] ?? response;
      if (data is List) {
        return data.map((json) => Supplier.fromJson(json as Map<String, dynamic>)).toList();
      }
      return [];
    } catch (e) {
      ErrorLogger.log('SupplierRepository.getSuppliers', e);
      return [];
    }
  }

  static Future<Supplier?> getSupplier(String id) async {
    try {
      final response = await ApiService.staticGet('suppliers/$id');
      return Supplier.fromJson(response);
    } catch (e) {
      ErrorLogger.log('SupplierRepository.getSupplier', e);
      return null;
    }
  }

  static Future<Supplier?> createSupplier(Supplier supplier) async {
    try {
      final response = await ApiService.staticPost(
        'suppliers',
        data: supplier.toJson(),
      );
      return Supplier.fromJson(response);
    } catch (e) {
      ErrorLogger.log('SupplierRepository.createSupplier', e);
      return null;
    }
  }

  static Future<Supplier?> updateSupplier(Supplier supplier) async {
    try {
      final response = await ApiService.staticPut(
        'suppliers/${supplier.id}',
        data: supplier.toJson(),
      );
      return Supplier.fromJson(response);
    } catch (e) {
      ErrorLogger.log('SupplierRepository.updateSupplier', e);
      return null;
    }
  }

  static Future<bool> deleteSupplier(String id) async {
    try {
      await ApiService.staticDelete('suppliers/$id');
      return true;
    } catch (e) {
      ErrorLogger.log('SupplierRepository.deleteSupplier', e);
      return false;
    }
  }
}