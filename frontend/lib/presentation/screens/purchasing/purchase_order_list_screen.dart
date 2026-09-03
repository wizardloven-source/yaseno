import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';

class PurchaseOrderListScreen extends StatefulWidget {
  const PurchaseOrderListScreen({super.key});

  @override
  State<PurchaseOrderListScreen> createState() => _PurchaseOrderListScreenState();
}

class _PurchaseOrderListScreenState extends State<PurchaseOrderListScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _orders = [];
  bool _isLoading = true;
  String? _error;
  String _statusFilter = '';

  @override
  void initState() {
    super.initState();
    _loadOrders();
  }

  Future<void> _loadOrders() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('purchase-orders', queryParameters: {
        if (_statusFilter.isNotEmpty) 'status': _statusFilter,
      });
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _orders = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Color _statusColor(String? status) {
    switch (status) {
      case 'draft': return AppColors.warning;
      case 'confirmed': return AppColors.secondary;
      case 'partially_received': return AppColors.warning;
      case 'received': return AppColors.success;
      case 'cancelled': return AppColors.danger;
      default: return AppColors.secondary;
    }
  }

  String _statusLabel(String? status) {
    switch (status) {
      case 'draft': return 'مسودة';
      case 'confirmed': return 'مؤكد';
      case 'partially_received': return 'مستلم جزئياً';
      case 'received': return 'مستلم';
      case 'cancelled': return 'ملغي';
      default: return status ?? '';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('أوامر الشراء'),
        centerTitle: true,
        actions: [
          PopupMenuButton<String?>(
            icon: const Icon(Icons.filter_list),
            onSelected: (v) {
              setState(() => _statusFilter = v ?? '');
              _loadOrders();
            },
            itemBuilder: (ctx) => [
              const PopupMenuItem(value: '', child: Text('الكل')),
              const PopupMenuItem(value: 'draft', child: Text('مسودة')),
              const PopupMenuItem(value: 'confirmed', child: Text('مؤكد')),
              const PopupMenuItem(value: 'partially_received', child: Text('مستلم جزئياً')),
              const PopupMenuItem(value: 'received', child: Text('مستلم')),
            ],
          ),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadOrders),
        ],
      ),
      body: _buildBody(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await context.push('/purchase-orders/create');
          _loadOrders();
        },
        backgroundColor: AppColors.success,
        foregroundColor: AppColors.textOnPrimary,
        icon: const Icon(Icons.add),
        label: const Text('أمر شراء جديد'),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const LoadingState();
    final filtered = _statusFilter.isEmpty
        ? _orders
        : _orders.where((o) => o['status'] == _statusFilter).toList();
    return Column(
      children: [
        if (_error != null)
          MaterialBanner(
            content: Text(ErrorUtils.sanitize(_error)),
            leading: const Icon(Icons.wifi_off, color: AppColors.warning),
            actions: [
              TextButton(onPressed: _loadOrders, child: const Text('إعادة المحاولة')),
            ],
            backgroundColor: AppColors.warningContainer,
          ),
        if (filtered.isEmpty && _error == null)
          Expanded(
            child: EmptyState(
              icon: Icons.shopping_cart_outlined,
              title: _statusFilter.isEmpty ? 'لا توجد أوامر شراء' : 'لا توجد نتائج',
              message: _statusFilter.isEmpty
                  ? 'لم يتم إنشاء أي أوامر شراء بعد'
                  : 'لا توجد أوامر شراء بهذه الحالة',
              actionLabel: _statusFilter.isEmpty ? 'أمر شراء جديد' : null,
              onAction: _statusFilter.isEmpty
                  ? () async {
                      await context.push('/purchase-orders/create');
                      _loadOrders();
                    }
                  : null,
            ),
          )
        else if (filtered.isNotEmpty)
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadOrders,
              child: ListView.builder(
                padding: const EdgeInsets.all(AppDimens.s3),
                itemCount: filtered.length,
                itemBuilder: (context, index) {
                  final order = filtered[index];
                  final status = order['status'] ?? 'draft';
                  return Card(
                    margin: const EdgeInsets.only(bottom: AppDimens.s2),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: _statusColor(status).withValues(alpha: 0.1),
                        child: Icon(Icons.shopping_cart, color: _statusColor(status)),
                      ),
                      title: Text(order['number'] ?? order['id'].toString().substring(0, 8),
                          style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('المورد: ${order['supplier_name'] ?? ''}'),
                          Text('العملة: ${order['currency'] ?? CurrencyHelper.baseCurrency}'),
                        ],
                      ),
                      trailing: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: _statusColor(status).withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                            ),
                            child: Text(_statusLabel(status),
                                style: TextStyle(color: _statusColor(status), fontSize: 11)),
                          ),
                          const SizedBox(height: 4),
                          Text(
                              formatMoneyCurrency(
                                parseMoney(order['total']) ?? Decimal.zero,
                                currency: (order['currency'] ?? '').toString(),
                              ),
                              style: const TextStyle(
                                  fontWeight: FontWeight.bold, fontSize: 12),
                            ),
                        ],
                      ),
                      onTap: () {
                        context.push('/purchase-orders/${order['id']}');
                      },
                    ),
                  );
                },
              ),
            ),
          )
        else
          const Expanded(child: SizedBox.shrink()),
      ],
    );
  }
}
