import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';

class SalesReturnScreen extends StatefulWidget {
  const SalesReturnScreen({super.key});

  @override
  State<SalesReturnScreen> createState() => _SalesReturnScreenState();
}

class _SalesReturnScreenState extends State<SalesReturnScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _invoices = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadInvoices();
  }

  Future<void> _loadInvoices() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('invoices', queryParameters: {
        'limit': 500,
      });
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      final all = (items as List).cast<Map<String, dynamic>>();
      setState(() {
        _invoices = all.where((inv) {
          final status = inv['status']?.toString() ?? '';
          return status == 'posted' || status == 'active';
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

  Future<void> _returnInvoice(Map<String, dynamic> invoice) async {
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('مرتجع فاتورة مبيعات'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('رقم الفاتورة: ${invoice['number'] ?? invoice['id']?.toString().substring(0, 8) ?? ''}'),
            Text('العميل: ${invoice['customer_name'] ?? ''}'),
            Text('المبلغ: ${invoice['total'] ?? 0} ${invoice['currency'] ?? 'USD'}'),
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
      final result = await _api.returnInvoice(
        invoice['id'].toString(),
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
        if (success) _loadInvoices();
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
        title: const Text('مرتجع المبيعات'),
        centerTitle: true,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadInvoices),
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
              TextButton(onPressed: _loadInvoices, child: const Text('إعادة المحاولة')),
            ],
            backgroundColor: AppColors.warningContainer,
          ),
          const Expanded(child: SizedBox.shrink()),
        ],
      );
    }

    if (_invoices.isEmpty) {
      return EmptyState(
        icon: Icons.replay,
        title: 'لا توجد فواتير مرحلة',
        message: 'لا توجد فواتير مبيعات مرحلة لإنشاء مرتجع منها',
      );
    }

    return RefreshIndicator(
      onRefresh: _loadInvoices,
      child: ListView.builder(
        padding: const EdgeInsets.all(AppDimens.s3),
        itemCount: _invoices.length,
        itemBuilder: (context, index) {
          final invoice = _invoices[index];
          final number = invoice['number'] ?? invoice['id']?.toString().substring(0, 8) ?? '';
          final customer = invoice['customer_name'] ?? '';
          final total = invoice['total'] ?? 0;
          final currency = invoice['currency'] ?? 'USD';
          return Card(
            margin: const EdgeInsets.only(bottom: AppDimens.s2),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: AppColors.danger.withValues(alpha: 0.1),
                child: const Icon(Icons.replay, color: AppColors.danger),
              ),
              title: Text(
                'فاتورة #$number',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('العميل: $customer'),
                  Text('المبلغ: $total $currency'),
                ],
              ),
              trailing: const Icon(Icons.arrow_forward_ios, size: 16),
              onTap: () => _returnInvoice(invoice),
            ),
          );
        },
      ),
    );
  }
}
