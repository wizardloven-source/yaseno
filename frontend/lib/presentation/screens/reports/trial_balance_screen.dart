import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';

class TrialBalanceReportScreen extends StatefulWidget {
  const TrialBalanceReportScreen({super.key});

  @override
  State<TrialBalanceReportScreen> createState() => _TrialBalanceReportScreenState();
}

class _TrialBalanceReportScreenState extends State<TrialBalanceReportScreen> {
  final ApiService _api = ApiService();
  DateTime _startDate = DateTime(DateTime.now().year, 1, 1);
  DateTime _endDate = DateTime.now();
  List<Map<String, dynamic>> _accounts = [];
  bool _isLoading = false;
  String? _error;
  Decimal _totalDebit = Decimal.zero;
  Decimal _totalCredit = Decimal.zero;
  String _currencySymbol = 'د.ع';

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
    _loadReport();
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

  Map<String, dynamic> _queryParams({String? format}) {
    return {
      'from_date': DateFormat('yyyy-MM-dd').format(_startDate),
      'to_date': DateFormat('yyyy-MM-dd').format(_endDate),
      if (format != null) 'format': format,
    };
  }

  Future<void> _loadReport() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response =
          await _api.get('reports/trial-balance', queryParameters: _queryParams());
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      final accounts = (items as List).cast<Map<String, dynamic>>();
      final totalDebit = moneySum(
          accounts.map((a) => a['debit'] ?? a['total_debit']));
      final totalCredit = moneySum(
          accounts.map((a) => a['credit'] ?? a['total_credit']));
      setState(() {
        _accounts = accounts;
        _totalDebit = totalDebit;
        _totalCredit = totalCredit;
        _isLoading = false;
      });
    } catch (e) {
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
      _loadReport();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ميزان المراجعة'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.picture_as_pdf),
            onPressed: () async {
              try {
                await _api.get('reports/trial-balance',
                    queryParameters: _queryParams(format: 'pdf'));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('تم تصدير الميزان بنجاح'), backgroundColor: AppColors.success),
                );
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
              }
            },
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
                TextButton(onPressed: _loadReport, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Container(
            padding: const EdgeInsets.all(AppDimens.s2),
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            child: Row(
              children: [
                _dateButton('من', _startDate, () => _pickDate(isStart: true)),
                const SizedBox(width: 12),
                _dateButton('إلى', _endDate, () => _pickDate(isStart: false)),
                const SizedBox(width: 12),
                AppButton(
                  onPressed: _loadReport,
                  icon: Icons.search,
                  label: 'عرض',
                ),
              ],
            ),
          ),
          if (_isLoading)
            const Expanded(child: LoadingState())
          else
            Expanded(
              child: Column(
                children: [
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.all(AppDimens.s2),
                      children: [
                        _buildTable(),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.all(AppDimens.s3),
                    color: AppColors.primaryContainer,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Column(
                          children: [
                            const Text('إجمالي المدين', style: AppTextStyles.statLabel),
                            Text(formatMoneyCurrency(_totalDebit, currency: _currencySymbol), style: AppTextStyles.moneyLarge.copyWith(color: AppColors.success)),
                          ],
                        ),
                        Column(
                          children: [
                            const Text('إجمالي الدائن', style: AppTextStyles.statLabel),
                            Text(formatMoneyCurrency(_totalCredit, currency: _currencySymbol), style: AppTextStyles.moneyLarge.copyWith(color: AppColors.danger)),
                          ],
                        ),
                        Column(
                          children: [
                            const Text('التوازن', style: AppTextStyles.statLabel),
                            Icon(
                              (_totalDebit - _totalCredit).abs() < Decimal.parse('0.01')
                                  ? Icons.check_circle
                                  : Icons.error,
                              color: (_totalDebit - _totalCredit).abs() < Decimal.parse('0.01')
                                  ? AppColors.success
                                  : AppColors.danger,
                              size: 24,
                            ),
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

  Widget _buildTable() {
    final rows = <DataRow>[
      ..._accounts.map((a) {
        final debit = parseMoney(a['debit'] ?? a['total_debit']) ?? Decimal.zero;
        final credit = parseMoney(a['credit'] ?? a['total_credit']) ?? Decimal.zero;
        final balance = parseMoney(a['balance']) ?? Decimal.zero;
        return DataRow(cells: [
          DataCell(Text('${a['account_code'] ?? ''}')),
          DataCell(Text('${a['name'] ?? a['account_name'] ?? ''}')),
          DataCell(Text(formatMoneyCurrency(parseMoney(a['opening_balance']) ?? Decimal.zero, currency: _currencySymbol))),
          DataCell(Text(formatMoneyCurrency(debit, currency: _currencySymbol), style: const TextStyle(color: AppColors.success))),
          DataCell(Text(formatMoneyCurrency(credit, currency: _currencySymbol), style: const TextStyle(color: AppColors.danger))),
          DataCell(Text(formatMoneyCurrency(balance, currency: _currencySymbol))),
        ]);
      }),
      DataRow(
        color: WidgetStatePropertyAll<Color?>(
          AppColors.primaryContainer,
        ),
        cells: [
          const DataCell(Text('الإجمالي', style: TextStyle(fontWeight: FontWeight.bold))),
          const DataCell(Text('')),
          const DataCell(Text('')),
          DataCell(Text(
            formatMoneyCurrency(_totalDebit, currency: _currencySymbol),
            style: AppTextStyles.moneyLarge.copyWith(color: AppColors.success),
          )),
          DataCell(Text(
            formatMoneyCurrency(_totalCredit, currency: _currencySymbol),
            style: AppTextStyles.moneyLarge.copyWith(color: AppColors.danger),
          )),
          DataCell(Text(
            formatMoneyCurrency(_totalDebit - _totalCredit, currency: _currencySymbol),
            style: AppTextStyles.moneyLarge,
          )),
        ],
      ),
    ];

    return DataTable(
      columns: const [
        DataColumn(label: Text('كود الحساب', style: TextStyle(fontWeight: FontWeight.bold))),
        DataColumn(label: Text('الاسم', style: TextStyle(fontWeight: FontWeight.bold))),
        DataColumn(label: Text('رصيد افتتاحي', style: TextStyle(fontWeight: FontWeight.bold)), numeric: true),
        DataColumn(label: Text('مدين', style: TextStyle(fontWeight: FontWeight.bold)), numeric: true),
        DataColumn(label: Text('دائن', style: TextStyle(fontWeight: FontWeight.bold)), numeric: true),
        DataColumn(label: Text('الرصيد', style: TextStyle(fontWeight: FontWeight.bold)), numeric: true),
      ],
      rows: rows,
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
