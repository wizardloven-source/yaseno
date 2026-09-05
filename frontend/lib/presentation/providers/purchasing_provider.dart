import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../domain/entities/purchase_order.dart';
import '../../services/api_service.dart';
import '../../utils/error_utils.dart';

class PurchasingProvider extends ChangeNotifier {
  final ApiService _apiService = ApiService();

  List<PurchaseOrder> _purchaseOrders = [];
  PurchaseOrder? _selectedOrder;
  bool _isLoading = false;
  String? _error;

  List<PurchaseOrder> get purchaseOrders => _purchaseOrders;
  PurchaseOrder? get selectedOrder => _selectedOrder;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadPurchaseOrders({
    String? status,
    String? supplierId,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.get('/purchase-orders', queryParameters: {
        if (status != null) 'status': status,
        if (supplierId != null) 'supplier_id': supplierId,
        if (fromDate != null) 'from_date': fromDate.toIso8601String().split('T')[0],
        if (toDate != null) 'to_date': toDate.toIso8601String().split('T')[0],
      });
      final items = response['items'] ?? response['purchase_orders'] ?? [];
      _purchaseOrders = (items is List ? items : [])
          .map((e) => PurchaseOrder.fromJson(e as Map<String, dynamic>))
          .toList();
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      _purchaseOrders = [];
    } finally {
      _setLoading(false);
    }
  }

  Future<PurchaseOrder> getPurchaseOrder(String id) async {
    try {
      final response = await _apiService.getPurchaseOrder(id);
      return PurchaseOrder.fromJson(response);
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    }
  }

  Future<PurchaseOrder> createPurchaseOrder({
    required String supplierId,
    required String supplierName,
    String? siteId,
    String currency = 'USD',
    String paymentTerms = 'net_30',
    DateTime? expectedDeliveryDate,
    required List<PurchaseLine> lines,
    String? notes,
    String createdBy = 'system',
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.createPurchaseOrder({
        'supplier_id': supplierId,
        'supplier_name': supplierName,
        if (siteId != null) 'site_id': siteId,
        'currency': currency,
        'payment_terms': paymentTerms,
        if (expectedDeliveryDate != null)
          'expected_delivery_date': expectedDeliveryDate.toIso8601String().split('T')[0],
        'lines': lines.map((l) => l.toJson()).toList(),
        if (notes != null) 'notes': notes,
        'created_by': createdBy,
      });
      final order = PurchaseOrder.fromJson(response);
      _purchaseOrders.insert(0, order);
      _error = null;
      return order;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> postPurchaseOrder(String id, String postedBy) async {
    _setLoading(true);
    try {
      final response = await _apiService.postPurchaseOrder(id);
      final order = PurchaseOrder.fromJson(response);
      final index = _purchaseOrders.indexWhere((o) => o.id == id);
      if (index != -1) {
        _purchaseOrders[index] = order;
      }
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> receivePurchaseLine({
    required String orderId,
    required String lineId,
    required Decimal quantity,
    required String receivedBy,
    String? batchNumber,
    List<String>? serialNumbers,
    DateTime? expiryDate,
    String? location,
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.receivePurchaseOrder(orderId, data: {
        'line_id': lineId,
        'quantity': quantity.toString(),
        'received_by': receivedBy,
        if (batchNumber != null) 'batch_number': batchNumber,
        if (serialNumbers != null) 'serial_numbers': serialNumbers,
        if (expiryDate != null) 'expiry_date': expiryDate.toIso8601String().split('T')[0],
        if (location != null) 'location': location,
      });
      final order = PurchaseOrder.fromJson(response);
      final index = _purchaseOrders.indexWhere((o) => o.id == orderId);
      if (index != -1) {
        _purchaseOrders[index] = order;
      }
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> receiveAllPurchaseOrder({
    required String orderId,
    required String receivedBy,
    Map<String, String>? batchNumbers,
    Map<String, List<String>>? serialNumbers,
    Map<String, DateTime?>? expiryDates,
    Map<String, String>? locations,
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.receivePurchaseOrder(orderId, data: {
        'received_by': receivedBy,
        'receive_all': true,
        if (batchNumbers != null) 'batch_numbers': batchNumbers,
        if (serialNumbers != null) 'serial_numbers': serialNumbers,
        if (expiryDates != null)
          'expiry_dates': expiryDates.map((k, v) => MapEntry(k, v?.toIso8601String().split('T')[0])),
        if (locations != null) 'locations': locations,
      });
      final order = PurchaseOrder.fromJson(response);
      final index = _purchaseOrders.indexWhere((o) => o.id == orderId);
      if (index != -1) {
        _purchaseOrders[index] = order;
      }
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> deleteDraftPurchaseOrder(String id) async {
    _setLoading(true);
    try {
      await _apiService.delete('/purchase-orders/$id');
      _purchaseOrders.removeWhere((o) => o.id == id);
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void setSelectedOrder(PurchaseOrder? order) {
    _selectedOrder = order;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
