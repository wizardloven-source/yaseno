import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import '../../../data/models/supplier_model.dart';
import '../../../data/repositories/supplier_repository.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/error_state.dart';
import '../../widgets/loading_state.dart';

class SuppliersListScreen extends StatefulWidget {
  const SuppliersListScreen({super.key});

  @override
  State<SuppliersListScreen> createState() => _SuppliersListScreenState();
}

class _SuppliersListScreenState extends State<SuppliersListScreen> {
  final ApiService _api = ApiService();
  List<Supplier> _suppliers = [];
  Map<String, Decimal> _balances = {};
  bool _isLoading = true;
  String? _error;
  String _filterStatus = 'active';
  String _searchText = '';

  @override
  void initState() {
    super.initState();
    _loadSuppliers();
    _loadBalances();
  }

  Future<void> _loadBalances() async {
    try {
      final response = await _api.get('suppliers');
      final items = response['items'] ?? response['data'] ?? [];
      if (items is List) {
        final balances = <String, Decimal>{};
        for (final item in items.cast<Map<String, dynamic>>()) {
          final id = (item['id'] ?? '').toString();
          final balance = item['balance'] ??
              item['outstanding_balance'] ??
              item['outstanding'] ??
              item['total_balance'];
          if (balance != null) {
            balances[id] = parseMoney(balance) ?? Decimal.zero;
          }
        }
        if (mounted) setState(() => _balances = balances);
      }
    } catch (e) {
      // silent fail, balances stay empty and "—" is shown
    }
  }

  Future<void> _loadSuppliers() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final suppliers = await SupplierRepository.getSuppliers(
        status: _filterStatus,
        limit: 100,
      );
      setState(() {
        _suppliers = suppliers;
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
        title: const Text('الموردين'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () => _showFilterDialog(),
          ),
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
      body: _buildBody(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _addSupplier(),
        backgroundColor: AppColors.success,
        foregroundColor: AppColors.textOnPrimary,
        icon: const Icon(Icons.add),
        label: const Text('مورد جديد'),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const LoadingState();
    }

    if (_error != null) {
      return ErrorState(
        message: ErrorUtils.sanitize(_error),
        onRetry: _loadSuppliers,
      );
    }

    if (_suppliers.isEmpty && _searchText.isEmpty) {
      return EmptyState(
        icon: Icons.business_outlined,
        title: 'لم تتم إضافة موردين بعد',
        message: 'أضف أول مورد لتبدأ تسجيل مشترياتك.',
        actionLabel: 'مورد جديد',
        onAction: _addSupplier,
      );
    }

    var filtered = _suppliers;
    if (_filterStatus != 'all') {
      filtered = filtered.where((s) => s.status == _filterStatus).toList();
    }
    if (_searchText.isNotEmpty) {
      final q = _searchText.toLowerCase();
      filtered = filtered.where((s) =>
        s.name.toLowerCase().contains(q) ||
        s.code.toLowerCase().contains(q) ||
        (s.phone ?? '').toLowerCase().contains(q)
      ).toList();
    }

    if (filtered.isEmpty) {
      return EmptyState(
        icon: Icons.search_off,
        title: 'لا توجد نتائج',
        actionLabel: 'مسح البحث',
        onAction: () => setState(() => _searchText = ''),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(AppDimens.s3),
      itemCount: filtered.length,
      itemBuilder: (context, index) {
        final supplier = filtered[index];
        return Card(
          margin: const EdgeInsets.only(bottom: AppDimens.s3),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: supplier.status == 'active'
                  ? AppColors.success
                  : AppColors.surfaceVariant,
              child: Text(
                supplier.code.substring(0, 1).toUpperCase(),
                style: const TextStyle(color: Colors.white),
              ),
            ),
            title: Text(
              supplier.name,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 4),
                Text('الكود: ${supplier.code}',
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                if (supplier.phone != null)
                  Text('الهاتف: ${supplier.phone}',
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                if (supplier.email != null)
                  Text('البريد: ${supplier.email}',
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                Text(
                  _balances.containsKey(supplier.id)
                      ? 'الرصيد المستحق: ${formatMoney(_balances[supplier.id])} ${supplier.currency}'
                      : 'الرصيد المستحق: —',
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: _getStatusColor(supplier.status),
                    borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                  ),
                  child: Text(
                    _getStatusText(supplier.status),
                    style: TextStyle(
                      fontSize: 12,
                      color: _getStatusTextColor(supplier.status),
                    ),
                  ),
                ),
              ],
            ),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  icon: const Icon(Icons.receipt_long, color: AppColors.secondary),
                  tooltip: 'كشف حساب',
                  onPressed: () => _viewStatement(supplier),
                ),
                PopupMenuButton<String>(
                  onSelected: (value) => _handleAction(value, supplier),
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: 'edit',
                      child: Row(
                        children: [
                          Icon(Icons.edit, color: AppColors.edit),
                          SizedBox(width: 8),
                          Text('تعديل'),
                        ],
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'toggle',
                      child: Row(
                        children: [
                          Icon(Icons.power_settings_new, color: AppColors.warning),
                          SizedBox(width: 8),
                          Text('تغيير الحالة'),
                        ],
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(Icons.delete, color: AppColors.danger),
                          SizedBox(width: 8),
                          Text('حذف', style: TextStyle(color: AppColors.danger)),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
            onTap: () => _viewSupplier(supplier),
          ),
        );
      },
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'active':
        return AppColors.successContainer;
      case 'inactive':
        return AppColors.surfaceVariant;
      case 'suspended':
        return AppColors.warningContainer;
      case 'blocked':
        return AppColors.errorContainer;
      default:
        return AppColors.surfaceVariant;
    }
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'active':
        return 'نشط';
      case 'inactive':
        return 'غير نشط';
      case 'suspended':
        return 'معلق';
      case 'blocked':
        return 'محظور';
      default:
        return status;
    }
  }

  Color _getStatusTextColor(String status) {
    switch (status) {
      case 'active':
        return AppColors.success;
      case 'inactive':
        return AppColors.textSecondary;
      case 'suspended':
        return AppColors.warning;
      case 'blocked':
        return AppColors.danger;
      default:
        return AppColors.textSecondary;
    }
  }

  void _addSupplier() {
    context.push('/suppliers/create').then((result) {
      if (result == true) _loadSuppliers();
    });
  }

  void _viewSupplier(Supplier supplier) {
    context.push('/suppliers/${supplier.id}').then((result) {
      if (result == true) _loadSuppliers();
    });
  }

  void _viewStatement(Supplier supplier) {
    context.push('/suppliers/${supplier.id}/statement?name=${Uri.encodeComponent(supplier.name)}');
  }

  void _handleAction(String value, Supplier supplier) {
    switch (value) {
      case 'edit':
        _viewSupplier(supplier);
        break;
      case 'toggle':
        _toggleStatus(supplier);
        break;
      case 'delete':
        _deleteSupplier(supplier);
        break;
    }
  }

  Future<void> _toggleStatus(Supplier supplier) async {
    final newStatus = supplier.status == 'active' ? 'inactive' : 'active';
    try {
      final updated = Supplier(
        id: supplier.id, code: supplier.code, name: supplier.name,
        email: supplier.email, phone: supplier.phone, mobile: supplier.mobile,
        street: supplier.street, city: supplier.city, country: supplier.country,
        taxNumber: supplier.taxNumber, creditLimit: supplier.creditLimit,
        currency: supplier.currency, notes: supplier.notes,
        status: newStatus, createdAt: supplier.createdAt, updatedAt: DateTime.now(),
        version: supplier.version,
      );
      final result = await SupplierRepository.updateSupplier(updated);
      if (result != null) {
        _loadSuppliers();
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('تم تغيير حالة المورد إلى ${_getStatusText(newStatus)}'), backgroundColor: AppColors.success));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل تغيير الحالة: ${ErrorUtils.sanitize(e)}'), backgroundColor: AppColors.danger));
    }
  }

  Future<void> _deleteSupplier(Supplier supplier) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف المورد "${supplier.name}"؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('حذف'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      final success = await SupplierRepository.deleteSupplier(supplier.id);
      if (success) {
        _loadSuppliers();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم حذف المورد بنجاح')),
        );
      }
    }
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تصفية الموردين'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RadioListTile<String>(
              title: const Text('الكل'),
              value: 'all',
              groupValue: _filterStatus,
              onChanged: (value) => setState(() => _filterStatus = value!),
            ),
            RadioListTile<String>(
              title: const Text('نشط'),
              value: 'active',
              groupValue: _filterStatus,
              onChanged: (value) => setState(() => _filterStatus = value!),
            ),
            RadioListTile<String>(
              title: const Text('غير نشط'),
              value: 'inactive',
              groupValue: _filterStatus,
              onChanged: (value) => setState(() => _filterStatus = value!),
            ),
            RadioListTile<String>(
              title: const Text('معلق'),
              value: 'suspended',
              groupValue: _filterStatus,
              onChanged: (value) => setState(() => _filterStatus = value!),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _loadSuppliers();
            },
            child: const Text('تطبيق'),
          ),
        ],
      ),
    );
  }
}