import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../domain/entities/invoice.dart';
import '../../services/api_service.dart';
import '../../utils/error_utils.dart';

class InvoicingProvider extends ChangeNotifier {
  final ApiService _apiService = ApiService();

  List<Invoice> _invoices = [];
  Invoice? _selectedInvoice;
  bool _isLoading = false;
  String? _error;

  List<Invoice> get invoices => _invoices;
  Invoice? get selectedInvoice => _selectedInvoice;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadInvoices({
    String? status,
    String? customerId,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.get('/invoices', queryParameters: {
        if (status != null) 'status': status,
        if (customerId != null) 'customer_id': customerId,
        if (fromDate != null) 'from_date': fromDate.toIso8601String().split('T')[0],
        if (toDate != null) 'to_date': toDate.toIso8601String().split('T')[0],
      });
      final items = response['items'] ?? response['invoices'] ?? [];
      _invoices = (items is List ? items : [])
          .map((e) => Invoice.fromJson(e as Map<String, dynamic>))
          .toList();
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      _invoices = [];
    } finally {
      _setLoading(false);
    }
  }

  Future<Invoice> getInvoice(String id) async {
    try {
      final response = await _apiService.getInvoice(id);
      return Invoice.fromJson(response);
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    }
  }

  Future<Invoice> createInvoice({
    required String customerId,
    required String customerName,
    String? customerBranchId,
    String? siteId,
    String currency = 'USD',
    String paymentCurrency = 'USD',
    String paymentType = 'cash',
    String? fundId,
    required List<InvoiceLine> lines,
    String? notes,
    bool isTaxInclusive = false,
    String createdBy = 'system',
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.post('/invoices', data: {
        'customer_id': customerId,
        'customer_name': customerName,
        if (customerBranchId != null) 'customer_branch_id': customerBranchId,
        if (siteId != null) 'site_id': siteId,
        'currency': currency,
        'payment_currency': paymentCurrency,
        'payment_type': paymentType,
        if (fundId != null) 'fund_id': fundId,
        'lines': lines.map((l) => l.toJson()).toList(),
        if (notes != null) 'notes': notes,
        'is_tax_inclusive': isTaxInclusive,
        'created_by': createdBy,
      });
      final invoice = Invoice.fromJson(response);
      _invoices.insert(0, invoice);
      _error = null;
      return invoice;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> postInvoice(String id, String postedBy) async {
    _setLoading(true);
    try {
      final response = await _apiService.postInvoice(id);
      final invoice = Invoice.fromJson(response);
      final index = _invoices.indexWhere((i) => i.id == id);
      if (index != -1) {
        _invoices[index] = invoice;
      }
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> cancelInvoice(String id, String reason, String cancelledBy) async {
    _setLoading(true);
    try {
      final response = await _apiService.cancelInvoice(id, reason: reason);
      final invoice = Invoice.fromJson(response);
      final index = _invoices.indexWhere((i) => i.id == id);
      if (index != -1) {
        _invoices[index] = invoice;
      }
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> deleteDraftInvoice(String id) async {
    _setLoading(true);
    try {
      await _apiService.delete('/invoices/$id');
      _invoices.removeWhere((i) => i.id == id);
      _error = null;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Future<Invoice> createReturnInvoice({
    required String originalInvoiceId,
    required String reason,
    required String createdBy,
  }) async {
    _setLoading(true);
    try {
      final response = await _apiService.returnInvoice(originalInvoiceId, reason: reason);
      final invoice = Invoice.fromJson(response);
      _invoices.insert(0, invoice);
      _error = null;
      return invoice;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      rethrow;
    } finally {
      _setLoading(false);
    }
  }

  Map<String, dynamic> getStatistics() {
    final total = _invoices.length;
    final posted = _invoices.where((i) => i.isPosted).length;
    final draft = _invoices.where((i) => i.isDraft).length;
    final cancelled = _invoices.where((i) => i.isCancelled).length;
    final totalAmount = _invoices.fold(Decimal.zero, (sum, i) => sum + i.total);

    return {
      'total': total,
      'posted': posted,
      'draft': draft,
      'cancelled': cancelled,
      'totalAmount': totalAmount,
    };
  }

  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  void setSelectedInvoice(Invoice? invoice) {
    _selectedInvoice = invoice;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
