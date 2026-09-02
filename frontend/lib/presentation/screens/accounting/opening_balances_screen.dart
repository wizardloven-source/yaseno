import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../data/models/accounting/account.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';

class OpeningBalancesScreen extends StatefulWidget {
  const OpeningBalancesScreen({super.key});

  @override
  State<OpeningBalancesScreen> createState() => _OpeningBalancesScreenState();
}

class _OpeningLineData {
  String? accountCode;
  String currency;
  Decimal debit = Decimal.zero;
  Decimal credit = Decimal.zero;
  final TextEditingController debitController = TextEditingController();
  final TextEditingController creditController = TextEditingController();
  final TextEditingController filterController = TextEditingController();

  _OpeningLineData({this.currency = 'USD'});

  void dispose() {
    debitController.dispose();
    creditController.dispose();
    filterController.dispose();
  }
}

class _OpeningBalancesScreenState extends State<OpeningBalancesScreen> {
  final ApiService _api = ApiService();
  bool _isLoading = true;
  bool _exists = false;
  String? _entryId;
  bool _isSaving = false;
  DateTime _openingDate = DateTime.now();
  final List<_OpeningLineData> _lines = [];
  List<Account> _accounts = [];
  List<Map<String, dynamic>> _currencies = [];
  String? _error;

  Decimal get _totalDebit => _lines.fold(Decimal.zero, (sum, l) => sum + l.debit);
  Decimal get _totalCredit => _lines.fold(Decimal.zero, (sum, l) => sum + l.credit);
  bool get _isBalanced => (_totalDebit - _totalCredit).abs() < Decimal.parse('0.01');

  @override
  void initState() {
    super.initState();
    _addLine();
    _loadData();
  }

  @override
  void dispose() {
    for (final line in _lines) {
      line.dispose();
    }
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      await Future.wait([_loadStatus(), _loadAccounts(), _loadCurrencies()]);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadStatus() async {
    try {
      final response = await _api.get('opening-balances');
      final data = response['data'] ?? response;
      final exists = data is Map ? (data['exists'] ?? false) : false;
      final entryId = data is Map ? data['entry_id'] : null;
      setState(() {
        _exists = exists == true;
        _entryId = entryId?.toString();
      });
    } catch (e) {
      setState(() => _error = ErrorUtils.sanitize(e));
    }
  }

  Future<void> _loadAccounts() async {
    try {
      final accounts = await _api.getAccounts();
      setState(() => _accounts = accounts);
    } catch (e) {
      setState(() => _error = ErrorUtils.sanitize(e));
    }
  }

  Future<void> _loadCurrencies() async {
    try {
      final currencies = await _api.getCurrencies();
      setState(() {
        _currencies = currencies;
        final base = _defaultCurrency;
        for (final line in _lines) {
          if (line.currency.isEmpty || line.currency == 'USD') {
            line.currency = base;
          }
        }
      });
    } catch (e) {
      setState(() => _error = ErrorUtils.sanitize(e));
    }
  }

  String get _defaultCurrency {
    for (final c in _currencies) {
      if (c['is_base'] == true) return c['code'] as String;
    }
    if (_currencies.isNotEmpty) return _currencies.first['code'] as String;
    return 'USD';
  }

  void _addLine() {
    setState(() {
      _lines.add(_OpeningLineData(currency: _defaultCurrency));
    });
  }

  void _removeLine(int index) {
    if (_lines.length <= 1) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('يجب أن يكون هناك سطر واحد على الأقل'),
          backgroundColor: AppColors.warning,
        ),
      );
      return;
    }
    setState(() {
      _lines[index].dispose();
      _lines.removeAt(index);
    });
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _openingDate,
      firstDate: DateTime(2020),
      lastDate: DateTime(2035),
    );
    if (picked != null) {
      setState(() => _openingDate = picked);
    }
  }

  List<Account> _filteredAccounts(_OpeningLineData line) {
    final query = line.filterController.text.trim().toLowerCase();
    if (query.isEmpty) return _accounts;
    return _accounts.where((a) {
      final code = a.code.toLowerCase();
      final name = a.name.toLowerCase();
      return code.contains(query) || name.contains(query);
    }).toList();
  }

  Future<void> _save() async {
    if (!_isBalanced) return;
    for (final line in _lines) {
      if (line.accountCode == null || line.accountCode!.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('يرجى اختيار الحساب لجميع الأسطر'),
            backgroundColor: AppColors.warning,
          ),
        );
        return;
      }
    }
    if (_totalDebit == 0 && _totalCredit == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('يرجى إدخال المبالغ'),
          backgroundColor: AppColors.warning,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);
    try {
      final lines = _lines.map((line) => {
            'account_code': line.accountCode,
            'debit': line.debit.toString(),
            'credit': line.credit.toString(),
            'currency': line.currency,
          }).toList();
      await _api.post('opening-balances', data: {
        'opening_date': DateFormat('yyyy-MM-dd').format(_openingDate),
        'lines': lines,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم حفظ الأرصدة الافتتاحية بنجاح'),
            backgroundColor: AppColors.success,
          ),
        );
        await _loadStatus();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الأرصدة الافتتاحية'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
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
                TextButton(onPressed: _loadData, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          if (_isLoading)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else
            Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_exists) return _buildExistsView();
    return _buildForm();
  }

  Widget _buildExistsView() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          color: AppColors.successContainer,
          elevation: 0,
          shadowColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppDimens.radiusCard),
            side: const BorderSide(color: AppColors.cardBorder),
          ),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                const Icon(Icons.check_circle, color: AppColors.success, size: 56),
                const SizedBox(height: 12),
                const Text(
                  'تم إدخال الأرصدة الافتتاحية',
                  style: AppTextStyles.headlineSmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  'رقم القيد: $_entryId',
                  style: AppTextStyles.bodyMedium,
                ),
                const SizedBox(height: 8),
                const Text(
                  'لا يمكن إعادة إدخال الأرصدة الافتتاحية بعد حفظها.',
                  style: AppTextStyles.bodySmall,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildForm() {
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              ListTile(
                title: Text(
                  'تاريخ الافتتاح: ${DateFormat('yyyy-MM-dd').format(_openingDate)}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                trailing: const Icon(Icons.calendar_today),
                shape: RoundedRectangleBorder(
                  side: BorderSide(color: AppColors.outline),
                  borderRadius: BorderRadius.circular(4),
                ),
                onTap: _pickDate,
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  const Text(
                    'الأسطر',
                    style: AppTextStyles.headlineSmall,
                  ),
                  const Spacer(),
                  TextButton.icon(
                    onPressed: _addLine,
                    icon: const Icon(Icons.add),
                    label: const Text('إضافة سطر'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ..._lines.asMap().entries.map((entry) {
                return _buildLineItem(entry.key, entry.value);
              }),
              const SizedBox(height: 16),
              _buildTotalsCard(),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.all(AppDimens.s3),
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            boxShadow: AppDimens.cardShadow,
          ),
          child: AppButton(
            label: 'حفظ الأرصدة',
            variant: AppButtonVariant.success,
            onPressed: _isBalanced ? _save : null,
            loading: _isSaving,
            expanded: true,
          ),
        ),
      ],
    );
  }

  Widget _buildLineItem(int index, _OpeningLineData line) {
    final filtered = _filteredAccounts(line);
    final selectedValid = line.accountCode != null &&
        filtered.any((a) => a.code == line.accountCode);
    return Card(
      margin: const EdgeInsets.only(bottom: AppDimens.s3),
      elevation: 0,
      shadowColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        side: const BorderSide(color: AppColors.cardBorder),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(radius: 14, child: Text('${index + 1}')),
                const SizedBox(width: 8),
                Text(
                  'سطر ${index + 1}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                IconButton(
                  onPressed: () => _removeLine(index),
                  icon: const Icon(Icons.delete, color: AppColors.danger),
                  iconSize: 20,
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: line.filterController,
              decoration: const InputDecoration(
                labelText: 'بحث عن حساب',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: selectedValid ? line.accountCode : null,
              hint: const Text('اختر الحساب'),
              decoration: const InputDecoration(
                labelText: 'الحساب',
                border: OutlineInputBorder(),
              ),
              items: filtered.map((a) {
                return DropdownMenuItem(
                  value: a.code,
                  child: Text(
                    '${a.code} - ${a.name}',
                    overflow: TextOverflow.ellipsis,
                  ),
                );
              }).toList(),
              onChanged: (value) {
                setState(() => line.accountCode = value);
              },
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: line.debitController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'مدين',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.arrow_downward),
                    ),
                    onChanged: (value) {
                      setState(() {
                        line.debit = parseMoney(value) ?? Decimal.zero;
                        if (line.debit > Decimal.zero) {
                          line.credit = Decimal.zero;
                          line.creditController.clear();
                        }
                      });
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: line.creditController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'دائن',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.arrow_upward),
                    ),
                    onChanged: (value) {
                      setState(() {
                        line.credit = parseMoney(value) ?? Decimal.zero;
                        if (line.credit > Decimal.zero) {
                          line.debit = Decimal.zero;
                          line.debitController.clear();
                        }
                      });
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _currencies.any((c) => c['code'] == line.currency)
                  ? line.currency
                  : null,
              decoration: const InputDecoration(
                labelText: 'العملة',
                border: OutlineInputBorder(),
              ),
              items: _currencies.map((c) {
                return DropdownMenuItem(
                  value: c['code'] as String,
                  child: Text('${c['code']} - ${c['name']}'),
                );
              }).toList(),
              onChanged: (value) {
                setState(() => line.currency = value ?? line.currency);
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTotalsCard() {
    final balanced = _isBalanced;
    return Container(
      padding: const EdgeInsets.all(AppDimens.s3),
      decoration: BoxDecoration(
        color: balanced ? AppColors.successContainer : AppColors.errorContainer,
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        border: Border.all(color: balanced ? AppColors.success : AppColors.danger),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('إجمالي المدين:'),
              Text(
                _totalDebit.toStringAsFixed(2),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('إجمالي الدائن:'),
              Text(
                _totalCredit.toStringAsFixed(2),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const Divider(),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'الفرق:',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: balanced ? AppColors.success : AppColors.danger,
                ),
              ),
              Text(
                (_totalDebit - _totalCredit).toStringAsFixed(2),
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: balanced ? AppColors.success : AppColors.danger,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Icon(
            balanced ? Icons.check_circle : Icons.error,
            color: balanced ? AppColors.success : AppColors.danger,
            size: 32,
          ),
          Text(
            balanced ? 'الأرصدة متوازنة' : 'الأرصدة غير متوازنة',
            style: TextStyle(
              color: balanced ? AppColors.success : AppColors.danger,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
