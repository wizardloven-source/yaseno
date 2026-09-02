import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../widgets/app_widgets.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';

class CustomerStatementScreen extends StatefulWidget {
  final String customerId;
  final String customerName;

  const CustomerStatementScreen({
    super.key,
    required this.customerId,
    required this.customerName,
  });

  @override
  State<CustomerStatementScreen> createState() => _CustomerStatementScreenState();
}

class _CustomerStatementScreenState extends State<CustomerStatementScreen> {
  final ApiService _api = ApiService();
  DateTime _fromDate = DateTime(DateTime.now().year, DateTime.now().month, 1);
  DateTime _toDate = DateTime.now();
  List<Map<String, dynamic>> _items = [];
  bool _isLoading = false;
  String? _error;
  Decimal _totalDebit = Decimal.zero;
  Decimal _totalCredit = Decimal.zero;
  Decimal _finalBalance = Decimal.zero;
  String _currencySymbol = 'د.ع';

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
    _loadStatement();
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

  Future<void> _loadStatement() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get(
        'customers/${widget.customerId}/statement',
        queryParameters: {
          'from_date': DateFormat('yyyy-MM-dd').format(_fromDate),
          'to_date': DateFormat('yyyy-MM-dd').format(_toDate),
        },
      );
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      Decimal totalDr = Decimal.zero, totalCr = Decimal.zero;
      for (final item in items) {
        totalDr += parseMoney(item['debit']) ?? Decimal.zero;
        totalCr += parseMoney(item['credit']) ?? Decimal.zero;
      }
      final list = (items as List).cast<Map<String, dynamic>>();
      final lastBalance = list.isNotEmpty
          ? parseMoney(list.last['balance']) ?? Decimal.zero
          : Decimal.zero;
      setState(() {
        _items = list;
        _totalDebit = totalDr;
        _totalCredit = totalCr;
        _finalBalance = lastBalance;
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
      initialDate: isStart ? _fromDate : _toDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _fromDate = picked;
        } else {
          _toDate = picked;
        }
      });
    }
  }

  String _formatDate(dynamic date) {
    if (date == null) return '';
    try {
      return DateFormat('yyyy-MM-dd').format(DateTime.parse(date.toString()));
    } catch (_) {
      return date.toString();
    }
  }

  (Color, String) _typeInfo(dynamic type) {
    final t = (type ?? '').toString().toLowerCase();
    switch (t) {
      case 'invoice':
        return (AppColors.success, 'فاتورة');
      case 'payment':
        return (AppColors.secondary, 'دفعة');
      case 'return':
        return (AppColors.warning, 'مرتجع');
      case 'cancel':
        return (AppColors.danger, 'إلغاء');
      default:
        return (AppColors.textMuted, t.isEmpty ? 'أخرى' : t);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('كشف حساب: ${widget.customerName}'),
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
            child: Row(
              children: [
                _dateButton('من', _fromDate, () => _pickDate(isStart: true)),
                const SizedBox(width: 8),
                _dateButton('إلى', _toDate, () => _pickDate(isStart: false)),
                const SizedBox(width: 8),
                AppButton(
                  label: 'تحديث',
                  icon: Icons.refresh,
                  onPressed: _isLoading ? null : _loadStatement,
                ),
              ],
            ),
          ),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _dateButton(String label, DateTime date, VoidCallback onPressed) {
    return Expanded(
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: const Icon(Icons.calendar_today, size: 18),
        label: Text(
          '$label: ${DateFormat('yyyy-MM-dd').format(date)}',
          style: const TextStyle(fontSize: 12),
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_items.isEmpty) {
      return const Center(child: Text('لا توجد حركات في هذه الفترة'));
    }
    return ListView(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columnSpacing: 16,
            columns: const [
              DataColumn(label: Text('التاريخ')),
              DataColumn(label: Text('البيان')),
              DataColumn(label: Text('مدين'), numeric: true),
              DataColumn(label: Text('دائن'), numeric: true),
              DataColumn(label: Text('الرصيد'), numeric: true),
            ],
            rows: _items.map((item) {
              final debit = parseMoney(item['debit']) ?? Decimal.zero;
              final credit = parseMoney(item['credit']) ?? Decimal.zero;
              final balance = parseMoney(item['balance']) ?? Decimal.zero;
              final (color, label) = _typeInfo(item['type']);
              final description = (item['description'] ?? '').toString();
              return DataRow(cells: [
                DataCell(Text(_formatDate(item['date']))),
                DataCell(
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: color.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                            ),
                            child: Text(
                              label,
                              style: TextStyle(
                                fontSize: 11,
                                color: color,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                      if (description.isNotEmpty)
                        Text(
                          description,
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.textSecondary,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                ),
                DataCell(
                  Text(
                    debit > Decimal.zero ? formatMoneyCurrency(debit, currency: _currencySymbol) : '-',
                    style: const TextStyle(color: AppColors.success),
                  ),
                ),
                DataCell(
                  Text(
                    credit > Decimal.zero ? formatMoneyCurrency(credit, currency: _currencySymbol) : '-',
                    style: const TextStyle(color: AppColors.danger),
                  ),
                ),
                DataCell(
                  Text(
                    formatMoneyCurrency(balance, currency: _currencySymbol),
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: balance >= Decimal.zero ? AppColors.success : AppColors.danger,
                    ),
                  ),
                ),
              ]);
            }).toList(),
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
                  Text(
                    formatMoneyCurrency(_totalDebit, currency: _currencySymbol),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: AppColors.success,
                    ),
                  ),
                ],
              ),
              Column(
                children: [
                  const Text('إجمالي الدائن', style: AppTextStyles.statLabel),
                  Text(
                    formatMoneyCurrency(_totalCredit, currency: _currencySymbol),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: AppColors.danger,
                    ),
                  ),
                ],
              ),
              Column(
                children: [
                  const Text('الرصيد النهائي', style: AppTextStyles.statLabel),
                  Text(
                    formatMoneyCurrency(_finalBalance, currency: _currencySymbol),
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: _finalBalance >= Decimal.zero ? AppColors.success : AppColors.danger,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}
