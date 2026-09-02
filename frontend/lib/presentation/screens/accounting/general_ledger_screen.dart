import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/error_logger.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';

class GeneralLedgerScreen extends StatefulWidget {
  const GeneralLedgerScreen({super.key});

  @override
  State<GeneralLedgerScreen> createState() => _GeneralLedgerScreenState();
}

class _GeneralLedgerScreenState extends State<GeneralLedgerScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _accounts = [];
  String? _selectedAccountCode;
  DateTime _startDate = DateTime(DateTime.now().year, 1, 1);
  DateTime _endDate = DateTime.now();
  List<Map<String, dynamic>> _statementItems = [];
  bool _isLoading = false;
  String? _error;
  Decimal _runningBalance = Decimal.zero;
  Decimal _totalDebit = Decimal.zero;
  Decimal _totalCredit = Decimal.zero;
  String _currencySymbol = 'د.ع';

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
    _loadAccounts();
  }

  Future<void> _loadBaseCurrency() async {
    try {
      final res = await _api.get('currency/base');
      final data = res['data'];
      if (data is Map && mounted) {
        setState(() => _currencySymbol = data['symbol'] ?? 'د.ع');
      }
    } catch (e, s) {
      await ErrorLogger.log('gl_base_currency', e, s);
    }
  }

  Future<void> _loadAccounts() async {
    try {
      final accounts = await _api.getAccounts();
      if (!mounted) return;
      setState(() {
        _accounts = accounts.map((a) => {'code': a.code, 'name': a.name}).toList();
      });
    } catch (e, s) {
      await ErrorLogger.log('gl_load_accounts', e, s);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  Future<void> _loadStatement() async {
    if (_selectedAccountCode == null) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get(
        'accounts/$_selectedAccountCode/statement',
        queryParameters: {
          'from_date': DateFormat('yyyy-MM-dd').format(_startDate),
          'to_date': DateFormat('yyyy-MM-dd').format(_endDate),
        },
      );
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];

      Decimal totalDebit = Decimal.zero;
      Decimal totalCredit = Decimal.zero;
      Decimal finalBalance = Decimal.zero;
      final List<Map<String, dynamic>> statement = [];

      for (final item in (items as List)) {
        final map = (item as Map).cast<String, dynamic>();
        final debit = parseMoney(map['debit']) ?? Decimal.zero;
        final credit = parseMoney(map['credit']) ?? Decimal.zero;
        totalDebit += debit;
        totalCredit += credit;
        final balance = parseMoney(map['balance']) ?? Decimal.zero;
        finalBalance = balance;
        statement.add(map);
      }

      setState(() {
        _statementItems = statement;
        _totalDebit = totalDebit;
        _totalCredit = totalCredit;
        _runningBalance = finalBalance;
        _isLoading = false;
      });
    } catch (e, s) {
      await ErrorLogger.log('gl_load_statement', e, s);
      if (!mounted) return;
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _pickDate({required bool isStart}) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: isStart ? _startDate : _endDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _startDate = picked;
        } else {
          _endDate = picked;
        }
      });
    }
  }

  void _openEntry(String? entryId) {
    if (entryId == null || entryId.isEmpty) return;
    context.go('/journal-entries/$entryId');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('دفتر الأستاذ العام'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadStatement, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Container(
            padding: const EdgeInsets.all(AppDimens.s3),
            color: AppColors.surfaceContainerHigh,
            child: Column(
              children: [
                DropdownButtonFormField<String>(
                  value: _selectedAccountCode,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'اختر الحساب',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: _accounts
                      .map((a) => DropdownMenuItem<String>(
                            value: (a['code'] ?? '').toString(),
                            child: Text('${a['code']} - ${a['name']}'),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _selectedAccountCode = v),
                ),
                const SizedBox(height: AppDimens.s3),
                Row(
                  children: [
                    _dateButton('من', _startDate, () => _pickDate(isStart: true)),
                    const SizedBox(width: AppDimens.s2),
                    _dateButton('إلى', _endDate, () => _pickDate(isStart: false)),
                    const SizedBox(width: AppDimens.s2),
                    AppButton(
                      label: 'عرض',
                      icon: Icons.search,
                      onPressed: _loadStatement,
                    ),
                  ],
                ),
              ],
            ),
          ),
          if (_isLoading)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else if (_selectedAccountCode == null)
            const Expanded(child: Center(child: Text('اختر حساباً لعرض كشف الحساب')))
          else
            Expanded(
              child: Column(
                children: [
                  Expanded(
                    child: _statementItems.isEmpty
                        ? const Center(child: Text('لا توجد حركات لهذا الحساب'))
                        : SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: SingleChildScrollView(
                              child: DataTable(
                                columnSpacing: 16,
                                columns: const [
                                  DataColumn(label: Text('التاريخ')),
                                  DataColumn(label: Text('البيان')),
                                  DataColumn(label: Text('مدين')),
                                  DataColumn(label: Text('دائن')),
                                  DataColumn(label: Text('الرصيد')),
                                ],
                                rows: _statementItems.map((item) {
                                  final balance = parseMoney(item['balance']) ?? Decimal.zero;
                                  final entryId = item['entry_id']?.toString();
                                  final open = entryId != null && entryId.isNotEmpty
                                      ? () => _openEntry(entryId)
                                      : null;
                                  final debitVal = parseMoney(item['debit']) ?? Decimal.zero;
                                  final creditVal = parseMoney(item['credit']) ?? Decimal.zero;
                                  return DataRow(cells: [
                                    _tapCell(Text(item['date']?.toString() ?? ''), open),
                                    _tapCell(
                                      Text(item['description']?.toString() ?? '', overflow: TextOverflow.ellipsis),
                                      open,
                                    ),
                                    DataCell(Text(
                                      debitVal > Decimal.zero
                                          ? formatMoneyCurrency(debitVal, currency: _currencySymbol)
                                          : '-',
                                      style: const TextStyle(color: AppColors.success),
                                    )),
                                    DataCell(Text(
                                      creditVal > Decimal.zero
                                          ? formatMoneyCurrency(creditVal, currency: _currencySymbol)
                                          : '-',
                                      style: const TextStyle(color: AppColors.danger),
                                    )),
                                    DataCell(Text(
                                      balance.toStringAsFixed(2),
                                      style: TextStyle(
                                        fontWeight: FontWeight.bold,
                                        color: balance >= Decimal.zero ? AppColors.success : AppColors.danger,
                                      ),
                                    )),
                                  ]);
                                }).toList(),
                              ),
                            ),
                          ),
                  ),
                  Container(
                    padding: const EdgeInsets.all(AppDimens.s3),
                    color: Theme.of(context).colorScheme.primaryContainer,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Column(
                          children: [
                            const Text('إجمالي المدين', style: AppTextStyles.statLabel),
                            Text(_totalDebit.toStringAsFixed(2),
                                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.success)),
                          ],
                        ),
                        Column(
                          children: [
                            const Text('إجمالي الدائن', style: AppTextStyles.statLabel),
                            Text(_totalCredit.toStringAsFixed(2),
                                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.danger)),
                          ],
                        ),
                        Column(
                          children: [
                            const Text('الرصيد النهائي', style: AppTextStyles.statLabel),
                            Text(_runningBalance.toStringAsFixed(2),
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  color: _runningBalance >= Decimal.zero ? AppColors.success : AppColors.danger,
                                )),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  DataCell _tapCell(Widget child, VoidCallback? onTap) {
    return DataCell(
      InkWell(
        onTap: onTap,
        child: Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: child),
      ),
    );
  }

  Widget _dateButton(String label, DateTime date, VoidCallback onPressed) {
    return Expanded(
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: const Icon(Icons.calendar_today, size: 18),
        label: Text('$label: ${DateFormat('yyyy-MM-dd').format(date)}', style: const TextStyle(fontSize: 12)),
      ),
    );
  }
}
