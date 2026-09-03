import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';

class AgingReportScreen extends StatefulWidget {
  final String mode;

  const AgingReportScreen({super.key, this.mode = 'customers'});

  @override
  State<AgingReportScreen> createState() => _AgingReportScreenState();
}

class _AgingReportScreenState extends State<AgingReportScreen> {
  final ApiService _api = ApiService();
  late String _mode;
  List<Map<String, dynamic>> _items = [];
  bool _isLoading = false;
  String? _error;
  Decimal _totalCurrent = Decimal.zero;
  Decimal _total30 = Decimal.zero;
  Decimal _total60 = Decimal.zero;
  Decimal _total90 = Decimal.zero;
  Decimal _totalAll = Decimal.zero;
  String _currencySymbol = 'د.ع';

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
    _mode = widget.mode;
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

  String get _title =>
      _mode == 'customers' ? 'تقادم الذمم المدينة' : 'تقادم الذمم الدائنة';

  String get _endpoint =>
      _mode == 'customers' ? 'customers/aging' : 'suppliers/aging';

  Future<void> _loadReport() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get(_endpoint);
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      final list = (items as List).cast<Map<String, dynamic>>();
      final totalCurrent = moneySum(list.map((e) => e['current']));
      final total30 = moneySum(list.map((e) => e['d30']));
      final total60 = moneySum(list.map((e) => e['d60']));
      final total90 = moneySum(list.map((e) => e['d90']));
      final totalAll = moneySum(list.map((e) => e['total']));
      setState(() {
        _items = list;
        _totalCurrent = totalCurrent;
        _total30 = total30;
        _total60 = total60;
        _total90 = total90;
        _totalAll = totalAll;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  void _switchMode(String mode) {
    if (mode == _mode) return;
    setState(() => _mode = mode);
    _loadReport();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_title),
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
            child: SegmentedButton<String>(
              segments: const [
                ButtonSegment(
                  value: 'customers',
                  label: Text('العملاء'),
                  icon: Icon(Icons.person),
                ),
                ButtonSegment(
                  value: 'suppliers',
                  label: Text('الموردين'),
                  icon: Icon(Icons.local_shipping),
                ),
              ],
              selected: {_mode},
              onSelectionChanged: (selection) => _switchMode(selection.first),
            ),
          ),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  DataCell _amountCell(Decimal value, Color color) {
    return DataCell(
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          formatMoneyCurrency(value, currency: _currencySymbol),
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const LoadingState();
    }
    if (_items.isEmpty) {
      return const EmptyState(
        icon: Icons.receipt_long_outlined,
        title: 'لا توجد بيانات',
      );
    }
    return ListView(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columnSpacing: 16,
            columns: const [
              DataColumn(label: Text('الاسم')),
              DataColumn(label: Text('جارٍ'), numeric: true),
              DataColumn(label: Text('30 يوم'), numeric: true),
              DataColumn(label: Text('60 يوم'), numeric: true),
              DataColumn(label: Text('90 يوم+'), numeric: true),
              DataColumn(label: Text('الإجمالي'), numeric: true),
            ],
            rows: _items.map((item) {
              return DataRow(cells: [
                DataCell(
                  Text(
                    (item['name'] ?? '').toString(),
                    style: const TextStyle(fontWeight: FontWeight.w500),
                  ),
                ),
                _amountCell(parseMoney(item['current']) ?? Decimal.zero, AppColors.success),
                _amountCell(parseMoney(item['d30']) ?? Decimal.zero, AppColors.warning),
                _amountCell(parseMoney(item['d60']) ?? Decimal.zero, AppColors.warning),
                _amountCell(parseMoney(item['d90']) ?? Decimal.zero, AppColors.danger),
                _amountCell(
                  parseMoney(item['total']) ?? Decimal.zero,
                  AppColors.primary,
                ),
              ]);
            }).toList(),
          ),
        ),
        Container(
          padding: const EdgeInsets.all(AppDimens.s3),
          color: AppColors.primaryContainer,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _totalColumn('جارٍ', _totalCurrent, AppColors.success),
              _totalColumn('30 يوم', _total30, AppColors.warning),
              _totalColumn('60 يوم', _total60, AppColors.warning),
              _totalColumn('90 يوم+', _total90, AppColors.danger),
              _totalColumn('الإجمالي', _totalAll, AppColors.textPrimary),
            ],
          ),
        ),
      ],
    );
  }

  Widget _totalColumn(String label, Decimal value, Color color) {
    return Column(
      children: [
        Text(label, style: const TextStyle(fontSize: 12)),
        Text(
          formatMoneyCurrency(value, currency: _currencySymbol),
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }
}