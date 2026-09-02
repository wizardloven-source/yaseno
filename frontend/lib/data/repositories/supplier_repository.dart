import '../models/supplier_model.dart';
import '../../services/api_service.dart';

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
      if (response['success'] == true) {
        final data = response['data'] as List;
        return data.map((json) => Supplier.fromJson(json)).toList();
      }
      return [];
    } catch (e) {
      print('Error fetching suppliers: $e');
      return [];
    }
  }

  static Future<Supplier?> getSupplier(String id) async {
    try {
      final response = await ApiService.staticGet('suppliers/$id');
      if (response['success'] == true) {
        return Supplier.fromJson(response['data']);
      }
      return null;
    } catch (e) {
      print('Error fetching supplier: $e');
      return null;
    }
  }

  static Future<Supplier?> createSupplier(Supplier supplier) async {
    try {
      final response = await ApiService.staticPost(
        'suppliers',
        data: supplier.toJson(),
      );
      if (response['success'] == true) {
        return Supplier.fromJson(response['data']);
      }
      return null;
    } catch (e) {
      print('Error creating supplier: $e');
      return null;
    }
  }

  static Future<Supplier?> updateSupplier(Supplier supplier) async {
    try {
      final response = await ApiService.staticPut(
        'suppliers/${supplier.id}',
        data: supplier.toJson(),
      );
      if (response['success'] == true) {
        return Supplier.fromJson(response['data']);
      }
      return null;
    } catch (e) {
      print('Error updating supplier: $e');
      return null;
    }
  }

  static Future<bool> deleteSupplier(String id) async {
    try {
      final response = await ApiService.staticDelete('suppliers/$id');
      return response['success'] == true;
    } catch (e) {
      print('Error deleting supplier: $e');
      return false;
    }
  }
}