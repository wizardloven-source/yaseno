import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import '../../../data/models/customer_model.dart';
import '../../../data/repositories/customer_repository.dart';
import '../../../services/api_service.dart';
import '../../../services/import/import_definitions.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/excel_import_screen.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/error_state.dart';
import '../../widgets/loading_state.dart';

class CustomersListScreen extends StatefulWidget {
  const CustomersListScreen({super.key});

  @override
  State<CustomersListScreen> createState() => _CustomersListScreenState();
}

class _CustomersListScreenState extends State<CustomersListScreen> {
  final ApiService _api = ApiService();
  List<Customer> _allCustomers = [];
  Map<String, Decimal> _balances = {};
  bool _isLoading = true;
  String? _error;
  String _filterStatus = 'active';
  String _searchText = '';

  List<Customer> get _filteredCustomers {
    var list = _allCustomers;
    if (_filterStatus != 'all') {
      list = list.where((c) => c.status == _filterStatus).toList();
    }
    if (_searchText.isNotEmpty) {
      final q = _searchText.toLowerCase();
      list = list.where((c) =>
        c.name.toLowerCase().contains(q) ||
        c.code.toLowerCase().contains(q) ||
        (c.phone ?? '').toLowerCase().contains(q) ||
        (c.email ?? '').toLowerCase().contains(q) ||
        (c.city ?? '').toLowerCase().contains(q)
      ).toList();
    }
    return list;
  }

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final results = await Future.wait([
        CustomerRepository.getCustomers(limit: 500),
        _loadBalances(),
      ]);
      _allCustomers = results[0] as List<Customer>;
      setState(() => _isLoading = false);
    } catch (e) {
      setState(() { _error = ErrorUtils.sanitize(e); _isLoading = false; });
    }
  }

  Future<void> _loadBalances() async {
    try {
      final response = await _api.get('customers');
      final items = response['items'] ?? response['data'] ?? [];
      if (items is List) {
        final balances = <String, Decimal>{};
        for (final item in items.cast<Map<String, dynamic>>()) {
          final id = (item['id'] ?? '').toString();
          final balance = item['balance'] ?? item['outstanding_balance'] ?? item['outstanding'];
          if (balance != null) balances[id] = parseMoney(balance) ?? Decimal.zero;
        }
        if (mounted) setState(() => _balances = balances);
      }
    } catch (_) {}
  }

  Decimal get _totalBalance => _filteredCustomers.fold(Decimal.zero, (s, c) => s + (_balances[c.id] ?? Decimal.zero));

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredCustomers;
    return Scaffold(
      appBar: AppBar(
        title: const Text('العملاء'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.file_upload_outlined),
            tooltip: 'استيراد من إكسل',
            onPressed: () => showExcelImport(
              context: context,
              type: ImportEntityType.customers,
            ).then((_) => _loadAll()),
          ),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadAll),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              onChanged: (v) => setState(() => _searchText = v),
              decoration: InputDecoration(
                hintText: 'بحث بالاسم أو الكود أو الهاتف...',
                prefixIcon: const Icon(Icons.search, size: 20),
                suffixIcon: _searchText.isNotEmpty
                  ? IconButton(icon: const Icon(Icons.clear, size: 18), onPressed: () => setState(() => _searchText = ''))
                  : null,
                filled: true,
                fillColor: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.3),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppDimens.radiusInput), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                isDense: true,
              ),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadAll, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(
            child: _isLoading
                ? const LoadingState()
                : Column(
                  children: [
                    _buildFilterBar(),
                    _buildSummaryHeader(),
                    Expanded(
                      child: filtered.isEmpty
                          ? _buildEmpty()
                          : ListView.separated(
                              padding: const EdgeInsets.all(AppDimens.s3),
                              itemCount: filtered.length,
                              separatorBuilder: (_, __) => const SizedBox(height: AppDimens.s2),
                              itemBuilder: (context, i) => _buildCustomerCard(filtered[i]),
                            ),
                    ),
                  ],
                ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addCustomer,
        backgroundColor: AppColors.success,
        foregroundColor: AppColors.textOnPrimary,
        icon: const Icon(Icons.add),
        label: const Text('عميل جديد'),
      ),
    );
  }

  Widget _buildError() {
    return ErrorState(
      message: ErrorUtils.sanitize(_error),
      onRetry: _loadAll,
    );
  }

  Widget _buildEmpty() {
    if (_searchText.isNotEmpty) {
      return EmptyState(
        icon: Icons.search_off,
        title: 'لا توجد نتائج',
        message: 'جرب كلمات بحث مختلفة أو امسح البحث.',
        actionLabel: 'مسح البحث',
        onAction: () => setState(() => _searchText = ''),
      );
    }
    return EmptyState(
      icon: Icons.people_outline,
      title: 'لم تتم إضافة عملاء بعد',
      message: 'أضف أول عميل لتبدأ تسجيل مبيعاتك.',
      actionLabel: 'عميل جديد',
      onAction: _addCustomer,
    );
  }

  Widget _buildFilterBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppDimens.s3, vertical: AppDimens.s2),
      child: Row(
        children: [
          _filterChip('الكل', 'all'),
          const SizedBox(width: 6),
          _filterChip('نشط', 'active'),
          const SizedBox(width: 6),
          _filterChip('غير نشط', 'inactive'),
        ],
      ),
    );
  }

  Widget _filterChip(String label, String value) {
    final selected = _filterStatus == value;
    return FilterChip(
      label: Text(label, style: TextStyle(fontSize: 12, color: selected ? Colors.white : null)),
      selected: selected,
      onSelected: (_) => setState(() => _filterStatus = value),
      selectedColor: AppColors.primary,
      checkmarkColor: Colors.white,
      visualDensity: VisualDensity.compact,
    );
  }

  Widget _buildSummaryHeader() {
    final count = _filteredCustomers.length;
    final active = _allCustomers.where((c) => c.status == 'active').length;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppDimens.s3, vertical: AppDimens.s2),
      child: Row(
        children: [
          _summaryChip('$count', 'عميل', AppColors.secondary),
          const SizedBox(width: AppDimens.s2),
          _summaryChip('$active', 'نشط', AppColors.success),
          const SizedBox(width: AppDimens.s2),
          _summaryChip(formatMoney(_totalBalance), 'الرصيد المستحق', AppColors.warning),
        ],
      ),
    );
  }

  Widget _summaryChip(String value, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(value, style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 13)),
          const SizedBox(width: 4),
          Text(label, style: TextStyle(fontSize: 11, color: color.withAlpha(180))),
        ],
      ),
    );
  }

  Widget _buildCustomerCard(Customer customer) {
    final balance = _balances[customer.id];
    final isActive = customer.status == 'active';
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: isActive ? AppColors.successContainer : AppColors.surfaceVariant,
          child: Text(customer.code.isNotEmpty ? customer.code.substring(0, 1).toUpperCase() : '?',
            style: TextStyle(color: isActive ? AppColors.success : AppColors.textSecondary, fontWeight: FontWeight.bold)),
        ),
        title: Text(customer.name, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 2),
            Row(
              children: [
                Text('${customer.code}', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                if (customer.phone != null && customer.phone!.isNotEmpty) ...[
                  const SizedBox(width: 8),
                  Icon(Icons.phone, size: 12, color: AppColors.textHint),
                  const SizedBox(width: 2),
                  Text(customer.phone!, style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                ],
                if (customer.city != null && customer.city!.isNotEmpty) ...[
                  const SizedBox(width: 8),
                  Icon(Icons.location_on, size: 12, color: AppColors.textHint),
                  const SizedBox(width: 2),
                  Text(customer.city!, style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                ],
              ],
            ),
            const SizedBox(height: 2),
            Row(
              children: [
                if (balance != null)
                  Text('الرصيد: ${formatMoney(balance)} ${customer.currency}',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: balance > Decimal.zero ? AppColors.danger : AppColors.success)),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: isActive ? AppColors.successContainer : AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                  ),
                  child: Text(isActive ? 'نشط' : 'غير نشط', style: TextStyle(fontSize: 11,
                    color: isActive ? AppColors.success : AppColors.textSecondary)),
                ),
              ],
            ),
          ],
        ),
        trailing: PopupMenuButton<String>(
          onSelected: (v) => _handleAction(v, customer),
          itemBuilder: (_) => [
            const PopupMenuItem(value: 'statement', child: Row(children: [Icon(Icons.receipt_long, size: 18), SizedBox(width: 8), Text('كشف حساب')])),
            const PopupMenuItem(value: 'edit', child: Row(children: [Icon(Icons.edit, size: 18), SizedBox(width: 8), Text('تعديل')])),
            PopupMenuItem(value: 'toggle', child: Row(children: [Icon(Icons.power_settings_new, size: 18),
              const SizedBox(width: 8), Text(isActive ? 'إيقاف' : 'تفعيل')])),
            const PopupMenuItem(value: 'delete', child: Row(children: [Icon(Icons.delete, size: 18, color: AppColors.danger),
              SizedBox(width: 8), Text('حذف', style: TextStyle(color: AppColors.danger))])),
          ],
        ),
        onTap: () => _editCustomer(customer),
      ),
    );
  }

  void _handleAction(String value, Customer customer) {
    switch (value) {
      case 'edit': _editCustomer(customer); break;
      case 'statement': _viewStatement(customer); break;
      case 'toggle': _toggleStatus(customer); break;
      case 'delete': _deleteCustomer(customer); break;
    }
  }

  void _addCustomer() {
    context.push('/customers/create').then((r) { if (r == true) _loadAll(); });
  }

  void _editCustomer(Customer customer) {
    context.push('/customers/${customer.id}').then((r) { if (r == true) _loadAll(); });
  }

  void _viewStatement(Customer customer) {
    context.push('/customers/${customer.id}/statement?name=${Uri.encodeComponent(customer.name)}');
  }

  Future<void> _toggleStatus(Customer customer) async {
    final newStatus = customer.status == 'active' ? 'inactive' : 'active';
    final success = await CustomerRepository.changeStatus(customer.id, newStatus);
    if (success) _loadAll();
  }

  Future<void> _deleteCustomer(Customer customer) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف العميل'),
        content: Text('هل أنت متأكد من حذف "${customer.name}"؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          AppButton(label: 'حذف', variant: AppButtonVariant.danger, onPressed: () => Navigator.pop(ctx, true)),
        ],
      ),
    );
    if (confirm == true) {
      final ok = await CustomerRepository.deleteCustomer(customer.id);
      if (ok) {
        _loadAll();
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم حذف العميل بنجاح'), backgroundColor: AppColors.success));
      }
    }
  }
}
