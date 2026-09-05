import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';

class PurchaseReturnScreen extends StatefulWidget {
  const PurchaseReturnScreen({super.key});

  @override
  State<PurchaseReturnScreen> createState() => _PurchaseReturnScreenState();
}

class _PurchaseReturnScreenState extends State<PurchaseReturnScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _orders = [];
  bool _isLoading = true;
  String? _error;

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
      final response = await _api.get('purchase-orders');
      final items = response['items'] ?? [];
      final all = (items as List).cast<Map<String, dynamic>>();
      setState(() {
        _orders = all.where((o) {
          final s = o['status']?.toString() ?? '';
          return s == 'posted' || s == 'confirmed' || s == 'received';
        }).toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _returnOrder(Map<String, dynamic> order) async {
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('مرتجع أمر شراء'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('رقم الأمر: ${order['number'] ?? order['id']?.toString().substring(0, 8) ?? ''}'),
            Text('المورد: ${order['supplier_name'] ?? ''}'),
            Text('المبلغ: ${order['total'] ?? 0} ${order['currency'] ?? 'USD'}'),
            const SizedBox(height: 12),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                labelText: 'سبب المرتجع',
                border: OutlineInputBorder(),
              ),
              minLines: 2,
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          ElevatedButton(
            onPressed: () {
              if (reasonController.text.trim().length < 2) {
                ScaffoldMessenger.of(ctx).showSnackBar(
                  const SnackBar(content: Text('أدخل سبباً للمرتجع (حرفين على الأقل)')),
                );
                return;
              }
              Navigator.pop(ctx, true);
            },
            child: const Text('تأكيد المرتجع'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final result = await _api.returnPurchaseOrder(
        order['id'].toString(),
        reason: reasonController.text.trim(),
      );
      if (mounted) {
        final success = result['success'] ?? false;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success
                ? (result['message'] ?? 'تم إنشاء المرتجع بنجاح')
                : (result['message'] ?? 'فشل إنشاء المرتجع')),
            backgroundColor: success ? AppColors.success : AppColors.danger,
          ),
        );
        if (success) _loadOrders();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('مرتجع المشتريات'),
        centerTitle: true,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadOrders),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const LoadingState();

    if (_error != null) {
      return Column(
        children: [
          MaterialBanner(
            content: Text(ErrorUtils.sanitize(_error)),
            leading: const Icon(Icons.wifi_off, color: AppColors.warning),
            actions: [
              TextButton(onPressed: _loadOrders, child: const Text('إعادة المحاولة')),
            ],
            backgroundColor: AppColors.warningContainer,
          ),
          const Expanded(child: SizedBox.shrink()),
        ],
      );
    }

    if (_orders.isEmpty) {
      return const EmptyState(
        icon: Icons.replay,
        title: 'لا توجد أوامر شراء مرحلة',
        message: 'لا توجد أوامر شراء مرحلة لإنشاء مرتجع منها',
      );
    }

    return RefreshIndicator(
      onRefresh: _loadOrders,
      child: ListView.builder(
        padding: const EdgeInsets.all(AppDimens.s3),
        itemCount: _orders.length,
        itemBuilder: (context, index) {
          final order = _orders[index];
          final number = order['number'] ?? order['id']?.toString().substring(0, 8) ?? '';
          final supplier = order['supplier_name'] ?? '';
          final total = order['total'] ?? 0;
          final currency = order['currency'] ?? 'USD';
          return Card(
            margin: const EdgeInsets.only(bottom: AppDimens.s2),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: AppColors.danger.withValues(alpha: 0.1),
                child: const Icon(Icons.replay, color: AppColors.danger),
              ),
              title: Text(
                'أمر شراء #$number',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('المورد: $supplier'),
                  Text('المبلغ: $total $currency'),
                ],
              ),
              trailing: const Icon(Icons.arrow_forward_ios, size: 16),
              onTap: () => _returnOrder(order),
            ),
          );
        },
      ),
    );
  }
}
