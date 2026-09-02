import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../widgets/app_widgets.dart';

class PaymentListScreen extends StatefulWidget {
  const PaymentListScreen({super.key});

  @override
  State<PaymentListScreen> createState() => _PaymentListScreenState();
}

class _PaymentListScreenState extends State<PaymentListScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _payments = [];
  bool _isLoading = true;
  String? _errorMessage;
  String _selectedFilter = 'all';

  @override
  void initState() {
    super.initState();
    _loadPayments();
  }

  Future<void> _loadPayments() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await _api.get('payments');
      final items = response['items'] ?? [];
      setState(() {
        _payments = items is List ? items.cast<Map<String, dynamic>>() : [];
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  List<Map<String, dynamic>> get _filteredPayments {
    if (_selectedFilter == 'all') return _payments;
    return _payments.where((p) {
      final status = (p['status'] ?? '').toString();
      return status == _selectedFilter;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('المدفوعات'),
        centerTitle: true,
        automaticallyImplyLeading: false,
      ),
      body: Column(
        children: [
          if (_errorMessage != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_errorMessage)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadPayments, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : Column(
                    children: [
                      _buildFilterBar(),
                      Expanded(
                        child: _filteredPayments.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(Icons.payments_outlined, size: 64, color: AppColors.textMuted),
                                    const SizedBox(height: 16),
                                    const Text('لا توجد مدفوعات'),
                                    const SizedBox(height: 8),
                                    AppButton(
                                      label: 'تسجيل دفعة جديدة',
                                      icon: Icons.add,
                                      variant: AppButtonVariant.success,
                                      onPressed: () => context.go('/payments/create'),
                                    ),
                                ],
                              ),
                            )
                          : RefreshIndicator(
                              onRefresh: _loadPayments,
                              child: ListView.builder(
                                padding: const EdgeInsets.all(16),
                                itemCount: _filteredPayments.length,
                                itemBuilder: (context, index) {
                                  return _buildPaymentCard(_filteredPayments[index]);
                                },
                              ),
                            ),
                    ),
                  ],
                ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go('/payments/create'),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildFilterBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          _buildFilterChip('الكل', 'all'),
          const SizedBox(width: 8),
          _buildFilterChip('مكتمل', 'completed'),
          const SizedBox(width: 8),
          _buildFilterChip('قيد الانتظار', 'pending'),
          const SizedBox(width: 8),
          _buildFilterChip('مرفوض', 'rejected'),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, String value) {
    final isSelected = _selectedFilter == value;
    return FilterChip(
      label: Text(label, style: TextStyle(fontSize: 12, color: isSelected ? Colors.white : AppColors.textSecondary)),
      selected: isSelected,
      selectedColor: AppColors.secondary,
      backgroundColor: AppColors.surfaceContainerHigh,
      onSelected: (selected) {
        setState(() => _selectedFilter = value);
      },
    );
  }

  Widget _buildPaymentCard(Map<String, dynamic> payment) {
    final amount = parseMoney(payment['amount']) ?? Decimal.zero;
    final status = (payment['status'] ?? '').toString();
    final paymentType = (payment['payment_type'] ?? '').toString();
    final dateStr = (payment['date'] ?? '').toString();
    final customerName = (payment['customer_name'] ?? payment['supplier_name'] ?? '').toString();
    final fundName = (payment['fund_name'] ?? '').toString();

    DateTime? date;
    if (dateStr.isNotEmpty) {
      try {
        date = DateTime.parse(dateStr);
      } catch (_) {}
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimens.radiusCard)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: paymentType == 'receive'
                        ? AppColors.successContainer
                        : AppColors.warningContainer,
                    borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                  ),
                  child: Icon(
                    paymentType == 'receive' ? Icons.arrow_downward : Icons.arrow_upward,
                    color: paymentType == 'receive' ? AppColors.success : AppColors.warning,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        customerName.isNotEmpty ? customerName : (payment['code'] ?? ''),
                        style: AppTextStyles.titleMedium,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        date != null
                            ? '${date.year}/${date.month.toString().padLeft(2, '0')}/${date.day.toString().padLeft(2, '0')}'
                            : '',
                        style: AppTextStyles.bodySmall,
                      ),
                    ],
                  ),
                ),
                _buildStatusBadge(status),
              ],
            ),
            const SizedBox(height: 12),
            const Divider(),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'المبلغ',
                      style: AppTextStyles.bodySmall,
                    ),
                    Text(
                          formatMoneyCurrency(
                          amount, currency: (payment['currency'] ?? CurrencyHelper.baseCurrency).toString()),
                      style: AppTextStyles.moneyMedium,
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'الصندوق',
                      style: AppTextStyles.bodySmall,
                    ),
                    Text(
                      fundName.isNotEmpty ? fundName : '-',
                      style: AppTextStyles.titleSmall,
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color color;
    String label;
    switch (status) {
      case 'completed':
        color = AppColors.success;
        label = 'مكتمل';
        break;
      case 'approved':
        color = AppColors.secondary;
        label = 'معتمد';
        break;
      case 'pending':
        color = AppColors.warning;
        label = 'قيد الانتظار';
        break;
      case 'rejected':
        color = AppColors.danger;
        label = 'مرفوض';
        break;
      case 'cancelled':
        color = AppColors.buttonCancel;
        label = 'ملغى';
        break;
      default:
        color = AppColors.buttonCancel;
        label = status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
