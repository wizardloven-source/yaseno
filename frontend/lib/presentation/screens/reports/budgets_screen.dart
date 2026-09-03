import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/error_state.dart';

class BudgetsScreen extends StatefulWidget {
  const BudgetsScreen({super.key});

  @override
  State<BudgetsScreen> createState() => _BudgetsScreenState();
}

class _BudgetsScreenState extends State<BudgetsScreen> {
  final ApiService _api = ApiService();

  List<Map<String, dynamic>> _budgets = [];
  List<Map<String, dynamic>> _accounts = [];
  bool _isLoading = true;
  String? _error;

  String? _selectedBudgetId;
  List<Map<String, dynamic>> _bvaItems = [];
  bool _bvaLoading = false;
  String? _bvaError;

  String _currencySymbol = 'د.ع';

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
    _loadData();
  }

  Future<void> _loadBaseCurrency() async {
    try {
      final res = await _api.get('currency/base');
      final data = res['data'];
      if (data is Map && mounted) {
        setState(() => _currencySymbol = data['symbol'] ?? 'د.ع');
      }
    } catch (_) {}
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final budgetsResponse = await _api.get('budgets');
      final budgetsData = budgetsResponse['data'] ?? budgetsResponse;
      final budgets = (budgetsData is Map ? budgetsData['items'] : budgetsData) ?? [];

      final accountsResponse = await _api.get('accounts');
      final accountsData = accountsResponse['data'] ?? accountsResponse;
      final accounts = (accountsData is Map ? accountsData['accounts'] ?? accountsData['items'] : accountsData) ?? [];

      setState(() {
        _budgets = (budgets as List).cast<Map<String, dynamic>>();
        _accounts = (accounts as List).cast<Map<String, dynamic>>();
        if (_selectedBudgetId == null && _budgets.isNotEmpty) {
          _selectedBudgetId = _budgets.first['id'].toString();
        }
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _loadBva() async {
    if (_selectedBudgetId == null) {
      _showSnack('اختر موازنة أولاً');
      return;
    }
    setState(() {
      _bvaLoading = true;
      _bvaError = null;
    });
    try {
      final response = await _api.get('reports/budget-vs-actual',
          queryParameters: {'budget_id': _selectedBudgetId});
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _bvaItems = (items as List).cast<Map<String, dynamic>>();
        _bvaLoading = false;
      });
    } catch (e) {
      setState(() {
        _bvaError = ErrorUtils.sanitize(e);
        _bvaLoading = false;
      });
    }
  }

  Future<void> _openNewBudgetDialog() async {
    final payload = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => _NewBudgetDialog(api: _api, accounts: _accounts),
    );
    if (payload != null && mounted) {
      try {
        await _api.post('budgets', data: payload);
        _showSnack('تم إنشاء الموازنة بنجاح', isError: false);
        await _loadData();
      } catch (e) {
        _showSnack(ErrorUtils.sanitize(e));
      }
    }
  }

  void _showSnack(String message, {bool isError = true}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: isError ? AppColors.danger : AppColors.success,
    ));
  }

  Decimal _num(dynamic v) => parseMoney(v) ?? Decimal.zero;

  String _statusLabel(String? status) {
    switch (status) {
      case 'draft':
        return 'مسودة';
      case 'active':
        return 'نشطة';
      case 'closed':
        return 'مغلقة';
      case 'approved':
        return 'معتمدة';
      default:
        return status ?? '-';
    }
  }

  Color _statusColor(String? status) {
    switch (status) {
      case 'active':
      case 'approved':
        return AppColors.success;
      case 'draft':
        return AppColors.warning;
      case 'closed':
        return AppColors.textHint;
      default:
        return AppColors.textHint;
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('الموازنات'),
          centerTitle: true,
          actions: [
            IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(text: 'الموازنات'),
              Tab(text: 'موازنة مقابل فعلي'),
            ],
          ),
        ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadData, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(
            child: TabBarView(
              children: [
                _buildBudgetsTab(),
                _buildBvaTab(),
              ],
            ),
          ),
        ],
      ),
        floatingActionButton: Builder(
          builder: (context) {
            final controller = DefaultTabController.of(context);
            if (controller.index != 0) return const SizedBox.shrink();
            return FloatingActionButton.extended(
              onPressed: _openNewBudgetDialog,
              icon: const Icon(Icons.add),
              label: const Text('موازنة جديدة'),
            );
          },
        ),
      ),
    );
  }

  Widget _buildBudgetsTab() {
    if (_isLoading) return const LoadingState();
    if (_budgets.isEmpty) {
      return const EmptyState(
        icon: Icons.pie_chart_outline,
        title: 'لا توجد موازنات',
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(AppDimens.s2),
      itemCount: _budgets.length,
      itemBuilder: (context, index) {
        final b = _budgets[index];
        final status = (b['status'] ?? '').toString();
        final start = (b['period_start'] ?? '').toString();
        final end = (b['period_end'] ?? '').toString();
        return Card(
          margin: const EdgeInsets.only(bottom: AppDimens.s2),
          elevation: 1,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimens.radiusCard)),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: _statusColor(status).withOpacity(0.1),
              child: Icon(Icons.pie_chart, color: _statusColor(status)),
            ),
            title: Text('${b['name'] ?? 'موازنة'}',
                style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Text(
                '${start.isNotEmpty ? start : '-'} → ${end.isNotEmpty ? end : '-'}'),
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: _statusColor(status).withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(_statusLabel(status),
                  style: TextStyle(
                      color: _statusColor(status),
                      fontSize: 12,
                      fontWeight: FontWeight.bold)),
            ),
          ),
        );
      },
    );
  }

  Widget _buildBvaTab() {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(AppDimens.s2),
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          child: Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _selectedBudgetId,
                  decoration: const InputDecoration(
                    labelText: 'الموازنة',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: _budgets
                      .map((b) => DropdownMenuItem(
                            value: b['id'].toString(),
                            child: Text('${b['name'] ?? 'موازنة'}'),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _selectedBudgetId = v),
                ),
              ),
              const SizedBox(width: 12),
              AppButton(
                onPressed: _loadBva,
                icon: Icons.search,
                label: 'عرض',
              ),
            ],
          ),
        ),
        Expanded(child: _buildBvaContent()),
      ],
    );
  }

  Widget _buildBvaContent() {
    if (_bvaLoading) return const LoadingState();
    if (_bvaError != null) {
      return ErrorState(
        message: ErrorUtils.sanitize(_bvaError),
        onRetry: _loadBva,
      );
    }
    if (_bvaItems.isEmpty) {
      return const EmptyState(
        icon: Icons.insert_chart_outlined,
        title: 'اختر موازنة ثم اضغط عرض',
      );
    }

    Decimal totalBudget = Decimal.zero;
    Decimal totalActual = Decimal.zero;
    Decimal totalVariance = Decimal.zero;
    for (final item in _bvaItems) {
      totalBudget += _num(item['budget']);
      totalActual += _num(item['actual']);
      totalVariance += _num(item['variance']);
    }
    final totalPct = totalBudget != Decimal.zero
        ? totalVariance.toDouble() / totalBudget.toDouble() * 100
        : 0.0;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(12),
      scrollDirection: Axis.vertical,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columnSpacing: 24,
          columns: const [
            DataColumn(label: Text('الحساب')),
            DataColumn(label: Text('الموازنة'), numeric: true),
            DataColumn(label: Text('الفعلي'), numeric: true),
            DataColumn(label: Text('الفرق'), numeric: true),
            DataColumn(label: Text('نسبة الفرق'), numeric: true),
          ],
          rows: [
            ..._bvaItems.map((item) {
              final budget = _num(item['budget']);
              final actual = _num(item['actual']);
              final variance = _num(item['variance']);
              final pct = budget != Decimal.zero
                  ? variance.toDouble() / budget.toDouble() * 100
                  : 0.0;
              final color = variance >= Decimal.zero ? AppColors.success : AppColors.danger;
              return DataRow(
                cells: [
                  DataCell(Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${item['account_code'] ?? item['code'] ?? ''}',
                          style: const TextStyle(fontWeight: FontWeight.bold)),
                      if (item['name'] != null)
                        Text('${item['name']}',
                            style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                    ],
                  )),
                  DataCell(Text(formatMoneyCurrency(budget, currency: _currencySymbol))),
                  DataCell(Text(formatMoneyCurrency(actual, currency: _currencySymbol))),
                  DataCell(Text(formatMoneyCurrency(variance, currency: _currencySymbol),
                      style: TextStyle(color: color, fontWeight: FontWeight.bold))),
                  DataCell(Text('${pct.toStringAsFixed(1)}%',
                      style: TextStyle(color: color, fontWeight: FontWeight.bold))),
                ],
              );
            }),
            DataRow(
              cells: [
                const DataCell(Text('الإجمالي',
                    style: TextStyle(fontWeight: FontWeight.bold))),
                DataCell(Text(formatMoneyCurrency(totalBudget, currency: _currencySymbol),
                    style: const TextStyle(fontWeight: FontWeight.bold))),
                DataCell(Text(formatMoneyCurrency(totalActual, currency: _currencySymbol),
                    style: const TextStyle(fontWeight: FontWeight.bold))),
                DataCell(Text(formatMoneyCurrency(totalVariance, currency: _currencySymbol),
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: totalVariance >= Decimal.zero ? AppColors.success : AppColors.danger))),
                DataCell(Text('${totalPct.toStringAsFixed(1)}%',
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: totalVariance >= Decimal.zero ? AppColors.success : AppColors.danger))),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _BudgetLine {
  String? accountCode;
  final TextEditingController amountController = TextEditingController();

  void dispose() => amountController.dispose();
}

class _NewBudgetDialog extends StatefulWidget {
  final ApiService api;
  final List<Map<String, dynamic>> accounts;

  const _NewBudgetDialog({required this.api, required this.accounts});

  @override
  State<_NewBudgetDialog> createState() => _NewBudgetDialogState();
}

class _NewBudgetDialogState extends State<_NewBudgetDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  DateTime _periodStart = DateTime(DateTime.now().year, 1, 1);
  DateTime _periodEnd = DateTime.now();
  final List<_BudgetLine> _lines = [];
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _lines.add(_BudgetLine());
  }

  @override
  void dispose() {
    _nameController.dispose();
    for (final l in _lines) {
      l.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDate({required bool isStart}) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: isStart ? _periodStart : _periodEnd,
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _periodStart = picked;
        } else {
          _periodEnd = picked;
        }
      });
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final lines = <Map<String, dynamic>>[];
    for (final l in _lines) {
      final amount = parseMoney(l.amountController.text.trim());
      if (l.accountCode != null && amount != null && amount != Decimal.zero) {
        lines.add({'account_code': l.accountCode, 'amount': amount});
      }
    }
    if (lines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('أضف بندًا واحدًا على الأقل بحساب ومبلغ صحيح')),
      );
      return;
    }
    setState(() => _isSaving = true);
    final payload = {
      'name': _nameController.text.trim(),
      'period_start': DateFormat('yyyy-MM-dd').format(_periodStart),
      'period_end': DateFormat('yyyy-MM-dd').format(_periodEnd),
      'lines': lines,
    };
    Navigator.pop(context, payload);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('موازنة جديدة'),
      content: SizedBox(
        width: 420,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'اسم الموازنة',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'مطلوب' : null,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickDate(isStart: true),
                        icon: const Icon(Icons.calendar_today, size: 18),
                        label: Text('من: ${DateFormat('yyyy-MM-dd').format(_periodStart)}',
                            style: const TextStyle(fontSize: 11)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickDate(isStart: false),
                        icon: const Icon(Icons.calendar_today, size: 18),
                        label: Text('إلى: ${DateFormat('yyyy-MM-dd').format(_periodEnd)}',
                            style: const TextStyle(fontSize: 11)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Text('بنود الموازنة',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                ..._lines.asMap().entries.map((entry) {
                  final index = entry.key;
                  final line = entry.value;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        Expanded(
                          flex: 3,
                          child: DropdownButtonFormField<String>(
                            value: line.accountCode,
                            decoration: const InputDecoration(
                              labelText: 'الحساب',
                              border: OutlineInputBorder(),
                              isDense: true,
                            ),
                            items: widget.accounts
                                .map((a) => DropdownMenuItem(
                                      value: a['code'].toString(),
                                      child: Text(
                                          '${a['code']} - ${a['name']}',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis),
                                    ))
                                .toList(),
                            onChanged: (v) => setState(() => line.accountCode = v),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          flex: 2,
                          child: TextFormField(
                            controller: line.amountController,
                            decoration: const InputDecoration(
                              labelText: 'المبلغ',
                              border: OutlineInputBorder(),
                              isDense: true,
                            ),
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.remove_circle_outline,
                              color: AppColors.danger),
                          onPressed: _lines.length > 1
                              ? () {
                                  setState(() {
                                    line.dispose();
                                    _lines.removeAt(index);
                                  });
                                }
                              : null,
                        ),
                      ],
                    ),
                  );
                }),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => setState(() => _lines.add(_BudgetLine())),
                    icon: const Icon(Icons.add),
                    label: const Text('إضافة بند'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('إلغاء'),
        ),
        AppButton(
          variant: AppButtonVariant.success,
          onPressed: _isSaving ? null : _save,
          loading: _isSaving,
          label: 'حفظ',
        ),
      ],
    );
  }
}