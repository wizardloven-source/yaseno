import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import '../../../services/import/import_definitions.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/excel_import_screen.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/status_chip.dart';

class InvoiceListScreen extends StatefulWidget {
  const InvoiceListScreen({super.key});

  @override
  State<InvoiceListScreen> createState() => _InvoiceListScreenState();
}

class _InvoiceListScreenState extends State<InvoiceListScreen> {
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
      final response = await _api.get('invoices');
      final items = response['items'] ?? [];
      setState(() {
        _invoices = items is List ? items.cast<Map<String, dynamic>>() : [];
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الفواتير'),
        centerTitle: true,
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.file_upload_outlined),
            tooltip: 'استيراد من إكسل',
            onPressed: () => showExcelImport(
              context: context,
              type: ImportEntityType.invoices,
            ).then((_) => _loadInvoices()),
          ),
        ],
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadInvoices, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(
            child: _isLoading
                ? const LoadingState()
                : _invoices.isEmpty
                    ? EmptyState(
                        icon: Icons.receipt_long_outlined,
                        title: 'لا توجد فواتير بعد',
                        message: 'أنشئ أول فاتورة لتبدأ تسجيل مبيعاتك.',
                        actionLabel: 'إنشاء فاتورة',
                        onAction: () => context.go('/invoices/create'),
                      )
                    : RefreshIndicator(
                        onRefresh: _loadInvoices,
                        child: ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _invoices.length,
                          itemBuilder: (context, index) {
                            return _buildInvoiceCard(_invoices[index]);
                        },
                      ),
                    ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go('/invoices/create'),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildInvoiceCard(Map<String, dynamic> invoice) {
    final id = (invoice['id'] ?? '').toString();
    final customerName = (invoice['customer_name'] ?? '').toString();
    final totalAmount = parseMoney(invoice['total_amount']) ?? Decimal.zero;
    final status = (invoice['status'] ?? '').toString();
    final currency = (invoice['currency'] ?? CurrencyHelper.baseCurrency).toString();
    final dateStr = (invoice['date'] ?? '').toString();

    DateTime? date;
    if (dateStr.isNotEmpty) {
      try {
        date = DateTime.parse(dateStr);
      } catch (_) {}
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppDimens.s3),
      child: AppCard(
        padding: EdgeInsets.zero,
        child: ListTile(
          contentPadding: const EdgeInsets.all(AppDimens.s3),
          leading: CircleAvatar(
            backgroundColor: AppColors.successContainer,
            child: Icon(Icons.receipt_long, color: AppColors.success),
          ),
          title: Text(
            customerName.isNotEmpty ? customerName : 'فاتورة #$id',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          subtitle: Text(
            date != null
                ? '${date.year}/${date.month.toString().padLeft(2, '0')}/${date.day.toString().padLeft(2, '0')}'
                : '',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
          ),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                formatMoneyCurrency(totalAmount, currency: currency),
                style: AppTextStyles.moneyMedium,
              ),
              const SizedBox(height: 4),
              StatusChip(status: status),
            ],
          ),
          onTap: () {
            context.go('/invoices/$id');
          },
        ),
      ),
    );
  }
}
