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

class IncomeStatementScreen extends StatefulWidget {
  const IncomeStatementScreen({super.key});

  @override
  State<IncomeStatementScreen> createState() => _IncomeStatementScreenState();
}

class _IncomeStatementScreenState extends State<IncomeStatementScreen> {
  final ApiService _api = ApiService();
  DateTime _startDate = DateTime(DateTime.now().year, 1, 1);
  DateTime _endDate = DateTime.now();
  Map<String, dynamic>? _reportData;
  bool _isLoading = false;
  String? _error;
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

  Decimal _num(dynamic v) => parseMoney(v) ?? Decimal.zero;

  String _fmtAmt(dynamic v) => formatMoneyCurrency(v, currency: _currencySymbol);

  bool _isEmptySection(dynamic data) {
    if (data == null) return true;
    if (data is Map) return data.isEmpty;
    if (data is List) return data.isEmpty;
    return false;
  }

  Color _sectionColor(String type) {
    switch (type) {
      case 'revenue':
      case 'income':
        return AppColors.success;
      case 'cogs':
      case 'cost_of_goods_sold':
        return AppColors.warning;
      case 'operating_expenses':
      case 'expenses':
        return AppColors.danger;
      case 'other_income':
        return AppColors.secondary;
      case 'other_expenses':
        return AppColors.danger;
      default:
        return AppColors.textHint;
    }
  }

  Future<void> _loadReport() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.post('reports/income-statement', data: {
        'period_start': DateFormat('yyyy-MM-dd').format(_startDate),
        'period_end': DateFormat('yyyy-MM-dd').format(_endDate),
      });
      setState(() {
        _reportData = response['data'] ?? response;
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
        title: const Text('قائمة الدخل'),
        centerTitle: true,
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
              child: ListView(
                padding: const EdgeInsets.all(AppDimens.s3),
                children: _reportData != null ? _buildReportRows() : [],
              ),
            ),
        ],
      ),
    );
  }

  List<Widget> _buildReportRows() {
    final data = _reportData!;
    final rows = <Widget>[];

    final sections = data['sections'];
    if (sections is List && sections.isNotEmpty) {
      for (final sec in sections) {
        if (sec is Map<String, dynamic>) {
          rows.add(_renderSection(sec));
        }
      }
    } else {
      // Revenue
      final revenue = data['revenue'] ?? data['incomes'];
      if (!_isEmptySection(revenue)) {
        rows.add(_renderAmountSection('الإيرادات', revenue, AppColors.success));
      }

      // COGS
      final cogs = data['cogs'] ??
          data['cost_of_goods_sold'] ??
          data['cost_of_sales'];
      if (!_isEmptySection(cogs)) {
        rows.add(_renderAmountSection('تكلفة البضاعة المباعة', cogs, AppColors.warning));
      }

      // Gross profit
      final hasGrossProfit =
          data.containsKey('gross_profit') || !_isEmptySection(cogs);
      if (hasGrossProfit) {
        final gp = data.containsKey('gross_profit')
            ? _num(data['gross_profit'])
            : _sectionTotal(revenue) - _sectionTotal(cogs);
        rows.add(_summaryRow('إجمالي الربح (الإيرادات - تكلفة المبيعات)', gp, false));
      }

      // Operating expenses
      final opEx = data['operating_expenses'] ??
          data['opex'] ??
          data['admin_expenses'] ??
          data['selling_expenses'];
      if (!_isEmptySection(opEx)) {
        rows.add(_renderAmountSection('المصاريف التشغيلية', opEx, AppColors.danger));
      }

      // Operating income / EBIT
      if (data.containsKey('operating_income') || data.containsKey('ebit')) {
        rows.add(_summaryRow(
            'الربح التشغيلي (EBIT)',
            _num(data['operating_income'] ?? data['ebit']),
            false));
      }

      // Other income / expense
      final otherIncome = data['other_income'];
      final otherExpenses = data['other_expenses'];
      if (!_isEmptySection(otherIncome)) {
        rows.add(_renderAmountSection('إيرادات أخرى', otherIncome, AppColors.secondary));
      }
      if (!_isEmptySection(otherExpenses)) {
        rows.add(
            _renderAmountSection('مصاريف أخرى', otherExpenses, AppColors.danger));
      }
    }

    // Generic items structure (defensive fallback)
    final items = data['items'];
    if (items is List && items.isNotEmpty) {
      rows.add(_renderItemsSection(items));
    }

    // Net income prominent
    final netIncome = _num(data['net_income'] ?? data['net_profit']);
    if (data.containsKey('net_income') ||
        data.containsKey('net_profit') ||
        netIncome != Decimal.zero) {
      rows.add(_netIncomeRow(netIncome));
    }

    return rows;
  }

  Decimal _sectionTotal(dynamic data) {
    if (data == null) return Decimal.zero;
    if (data is Map) {
      return moneySum(data.values);
    }
    if (data is List) {
      return moneySum(data.map((e) {
        if (e is Map) {
          return e['amount'] ?? e['balance'] ?? e['total'];
        }
        return e;
      }));
    }
    return _num(data);
  }

  Widget _renderSection(Map<String, dynamic> section) {
    final title = section['name'] ?? section['title'] ?? 'قسم';
    final type = (section['type'] ?? '').toString();
    final items = section['items'] ?? section['lines'] ?? {};
    return _renderAmountSection(title.toString(), items, _sectionColor(type));
  }

  Widget _renderItemsSection(List<dynamic> items) {
    final rows = <Widget>[];
    for (final e in items) {
      if (e is Map) {
        final name = e['name'] ?? e['account_name'] ?? e['account_code'] ?? e['code'] ?? '';
        final amount = _num(e['amount'] ?? e['balance'] ?? e['total']);
        final type = (e['type'] ?? '').toString();
        rows.add(Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('$name'),
              Text(_fmtAmt(amount),
                  style: TextStyle(
                      fontWeight: FontWeight.bold, color: _sectionColor(type))),
            ],
          ),
        ));
      }
    }
    return Card(
      margin: const EdgeInsets.only(bottom: AppDimens.s2),
      child: Padding(
        padding: const EdgeInsets.all(AppDimens.s2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('بنود قائمة الدخل',
                style: AppTextStyles.titleMedium),
            const Divider(),
            ...rows,
          ],
        ),
      ),
    );
  }

  Widget _renderAmountSection(String title, dynamic data, Color color) {
    final entries = <(String, Decimal)>[];
    if (data is Map) {
      data.forEach((k, v) => entries.add((k.toString(), _num(v))));
    } else if (data is List) {
      for (final e in data) {
        if (e is Map) {
          final name = e['name'] ??
              e['account_name'] ??
              e['account_code'] ??
              e['code'] ??
              '';
          entries.add(
              (name.toString(), _num(e['amount'] ?? e['balance'] ?? e['total'])));
        } else {
          entries.add(('', _num(e)));
        }
      }
    } else {
      entries.add(('', _num(data)));
    }
    final total = entries.fold<Decimal>(Decimal.zero, (s, e) => s + e.$2);

    return Card(
      margin: const EdgeInsets.only(bottom: AppDimens.s2),
      child: Padding(
        padding: const EdgeInsets.all(AppDimens.s2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title,
                    style: AppTextStyles.titleMedium.copyWith(color: color)),
                Text(_fmtAmt(total),
                    style: TextStyle(
                        fontSize: 14, fontWeight: FontWeight.bold, color: color)),
              ],
            ),
            const Divider(),
            ...entries.map((e) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(e.$1),
                      Text(_fmtAmt(e.$2),
                          style: const TextStyle(fontWeight: FontWeight.bold)),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }

  Widget _summaryRow(String label, Decimal value, bool isSub) {
    final color = value >= Decimal.zero ? AppColors.success : AppColors.danger;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: TextStyle(
                  fontSize: isSub ? 15 : 16, fontWeight: FontWeight.bold)),
          Text(_fmtAmt(value),
              style: TextStyle(
                  fontSize: isSub ? 15 : 16,
                  fontWeight: FontWeight.bold,
                  color: color)),
        ],
      ),
    );
  }

  Widget _netIncomeRow(Decimal value) {
    final isProfit = value >= Decimal.zero;
    return Container(
      margin: const EdgeInsets.only(top: AppDimens.s2),
      padding: const EdgeInsets.all(AppDimens.s3),
      decoration: BoxDecoration(
        color: isProfit ? AppColors.successContainer : AppColors.errorContainer,
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        border: Border.all(color: isProfit ? AppColors.success : AppColors.danger),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text('صافي الربح / الخسارة', style: AppTextStyles.titleLarge),
          Text(
            _fmtAmt(value),
            style: AppTextStyles.moneyLarge.copyWith(
              color: isProfit ? AppColors.success : AppColors.danger,
            ),
          ),
        ],
      ),
    );
  }

  Widget _dateButton(String label, DateTime date, VoidCallback onPressed) {
    return Expanded(
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: const Icon(Icons.calendar_today, size: 18),
        label: Text('$label: ${DateFormat('yyyy-MM-dd').format(date)}',
            style: const TextStyle(fontSize: 12)),
      ),
    );
  }
}