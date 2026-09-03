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

class BalanceSheetScreen extends StatefulWidget {
  const BalanceSheetScreen({super.key});

  @override
  State<BalanceSheetScreen> createState() => _BalanceSheetScreenState();
}

class _BalanceSheetScreenState extends State<BalanceSheetScreen> {
  final ApiService _api = ApiService();
  DateTime _asOfDate = DateTime.now();
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
      final response = await _api.post('reports/balance-sheet', data: {
        'as_of_date': DateFormat('yyyy-MM-dd').format(_asOfDate),
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

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _asOfDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() => _asOfDate = picked);
      _loadReport();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الميزانية العمومية'),
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
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _pickDate,
                    icon: const Icon(Icons.calendar_today, size: 18),
                    label: Text('بتاريخ: ${DateFormat('yyyy-MM-dd').format(_asOfDate)}',
                        style: const TextStyle(fontSize: 12)),
                  ),
                ),
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
                children: [
                  if (_reportData != null) ...[
                    _section('الأصول', _reportData!['assets'] ?? {}, AppColors.secondary),
                    _section('الخصوم', _reportData!['liabilities'] ?? {}, AppColors.danger),
                    _section('حقوق الملكية', _reportData!['equity'] ?? _reportData!['owners_equity'] ?? {}, AppColors.success),
                    const Divider(thickness: 2),
                    _balanceCheck(),
                  ],
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _balanceCheck() {
    if (_reportData == null) return const SizedBox();
    final totalAssets = parseMoney(_reportData!['total_assets']) ?? Decimal.zero;
    final totalLiabilities = parseMoney(_reportData!['total_liabilities']) ?? Decimal.zero;
    final totalEquity = parseMoney(_reportData!['total_equity']) ?? Decimal.zero;
    final isBalanced =
        (totalAssets - totalLiabilities - totalEquity).abs() <
            Decimal.parse('0.01');

    return Container(
      padding: const EdgeInsets.all(AppDimens.s3),
      decoration: BoxDecoration(
        color: isBalanced ? AppColors.successContainer : AppColors.errorContainer,
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        border: Border.all(color: isBalanced ? AppColors.success : AppColors.danger),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(isBalanced ? Icons.check_circle : Icons.error, color: isBalanced ? AppColors.success : AppColors.danger),
              const SizedBox(width: 8),
              Text(
                isBalanced ? 'الميزانية متوازنة' : 'الميزانية غير متوازنة!',
                style: AppTextStyles.headlineSmall.copyWith(
                  color: isBalanced ? AppColors.success : AppColors.danger,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _summaryItem('الأصول', totalAssets, AppColors.secondary),
              _summaryItem('الخصوم', totalLiabilities, AppColors.danger),
              _summaryItem('حقوق الملكية', totalEquity, AppColors.success),
            ],
          ),
        ],
      ),
    );
  }

  Widget _summaryItem(String label, Decimal value, Color color) {
    return Column(
      children: [
        Text(label, style: AppTextStyles.statLabel),
        Text(formatMoneyCurrency(value, currency: _currencySymbol), style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color)),
      ],
    );
  }

  Widget _section(String title, dynamic data, Color color) {
    final items = data is Map ? data : {};
    return Card(
      margin: const EdgeInsets.only(bottom: AppDimens.s2),
      child: Padding(
        padding: const EdgeInsets.all(AppDimens.s2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: AppTextStyles.titleMedium.copyWith(color: color)),
            const Divider(),
            ...items.entries.map((e) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('${e.key}'),
                  Text('${e.value}', style: TextStyle(fontWeight: FontWeight.bold, color: color)),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }
}
