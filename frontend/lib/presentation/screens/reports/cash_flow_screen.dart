import 'package:flutter/material.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';

class CashFlowScreen extends StatefulWidget {
  const CashFlowScreen({super.key});

  @override
  State<CashFlowScreen> createState() => _CashFlowScreenState();
}

class _CashFlowScreenState extends State<CashFlowScreen> {
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

  Future<void> _loadReport() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.getCashFlowReport(_startDate, _endDate);
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
        if (isStart) _startDate = picked;
        else _endDate = picked;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('قائمة التدفقات النقدية'),
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
                  onPressed: _isLoading ? null : _loadReport,
                  icon: Icons.search,
                  loading: _isLoading,
                  label: 'عرض',
                ),
              ],
            ),
          ),
          if (_isLoading)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else if (_reportData == null)
            const Expanded(child: Center(child: Text('اختر الفترة الزمنية واضغط عرض')))
          else
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(AppDimens.s3),
                children: [
                  _buildReport(),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildReport() {
    final operating = _reportData!['operating_activities'] ?? _reportData!['operating'] ?? {};
    final investing = _reportData!['investing_activities'] ?? _reportData!['investing'] ?? {};
    final financing = _reportData!['financing_activities'] ?? _reportData!['financing'] ?? {};
    final netCashFlow =
        parseMoney(_reportData!['net_cash_flow'] ?? _reportData!['net']) ??
            Decimal.zero;

    return Column(
      children: [
        _activitySection('الأنشطة التشغيلية', operating, AppColors.secondary),
        _activitySection('الأنشطة الاستثمارية', investing, AppColors.warning),
        _activitySection('الأنشطة التمويلية', financing, AppColors.secondary),
        const Divider(thickness: 2),
        Container(
          padding: const EdgeInsets.all(AppDimens.s3),
          decoration: BoxDecoration(
            color: AppColors.primaryContainer,
            borderRadius: BorderRadius.circular(AppDimens.radiusCard),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('صافي التدفق النقدي', style: AppTextStyles.titleLarge),
              Text(
                formatMoneyCurrency(netCashFlow, currency: _currencySymbol),
                style: AppTextStyles.moneyLarge.copyWith(
                  color: netCashFlow >= Decimal.zero ? AppColors.success : AppColors.danger,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _activitySection(String title, dynamic data, Color color) {
    final items = data is Map ? data : {};
    final entries =
        items.entries.where((e) => parseMoney(e.value) != null).toList();
    final subtotal = moneySum(entries.map((e) => e.value));

    return Card(
      margin: const EdgeInsets.only(bottom: AppDimens.s2),
      child: Padding(
        padding: const EdgeInsets.all(AppDimens.s2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: AppTextStyles.titleMedium.copyWith(color: color)),
            const Divider(),
            if (entries.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text('لا توجد بيانات', style: TextStyle(color: AppColors.textSecondary)),
              )
            else
              DataTable(
                columnSpacing: 24,
                columns: const [
                  DataColumn(label: Text('البيان')),
                  DataColumn(label: Text('المبلغ'), numeric: true),
                ],
                rows: entries.map((e) {
                  final val = parseMoney(e.value) ?? Decimal.zero;
                  return DataRow(cells: [
                    DataCell(Text(e.key.toString())),
                    DataCell(Text(
                      formatMoneyCurrency(val, currency: _currencySymbol),
                      style: TextStyle(
                        color: val >= Decimal.zero ? AppColors.success : AppColors.danger,
                        fontWeight: FontWeight.bold,
                      ),
                    )),
                  ]);
                }).toList(),
              ),
            const Divider(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('المجموع الفرعي - $title', style: const TextStyle(fontWeight: FontWeight.bold)),
                Text(
                  formatMoneyCurrency(subtotal, currency: _currencySymbol),
                  style: AppTextStyles.moneyMedium.copyWith(
                    color: subtotal >= Decimal.zero ? AppColors.success : AppColors.danger,
                  ),
                ),
              ],
            ),
          ],
        ),
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
