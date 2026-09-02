import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../widgets/app_widgets.dart';

class FundDetailScreen extends StatefulWidget {
  final String fundId;
  final String fundName;

  const FundDetailScreen({super.key, required this.fundId, required this.fundName});

  @override
  State<FundDetailScreen> createState() => _FundDetailScreenState();
}

class _FundDetailScreenState extends State<FundDetailScreen> {
  final ApiService _api = ApiService();
  Map<String, dynamic>? _fund;
  Decimal? _balance;
  DateTime _startDate = DateTime(DateTime.now().year, 1, 1);
  DateTime _endDate = DateTime.now();
  List<Map<String, dynamic>> _ledger = [];
  bool _isLoading = true;
  bool _isLoadingLedger = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadFund();
  }

  Future<void> _loadFund() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final fundResponse = await _api.get('funds/${widget.fundId}');
      final fund = fundResponse['data'] ?? fundResponse;
      final fundMap = fund is Map<String, dynamic> ? fund : Map<String, dynamic>.from(fund as Map);
      Decimal? balance;
      try {
        final balResp = await _api.get('funds/${widget.fundId}/balance');
        final balData = balResp['data'] ?? balResp;
        final b = balData['current_balance'] ?? balData['balance'] ?? balData['amount'];
        if (b != null) balance = parseMoney(b);
      } catch (_) {}
      setState(() {
        _fund = fundMap;
        if (balance != null) _balance = balance;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _loadLedger() async {
    setState(() {
      _isLoadingLedger = true;
      _error = null;
    });
    try {
      final response = await _api.get(
        'funds/${widget.fundId}/ledger',
        queryParameters: {
          'from_date': DateFormat('yyyy-MM-dd').format(_startDate),
          'to_date': DateFormat('yyyy-MM-dd').format(_endDate),
        },
      );
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _ledger = (items as List).cast<Map<String, dynamic>>();
        _isLoadingLedger = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoadingLedger = false;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('تفاصيل الصندوق: ${widget.fundName}'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'تحديث',
            onPressed: () {
              _loadFund();
              _loadLedger();
            },
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());

    return Column(
      children: [
        if (_error != null)
          MaterialBanner(
            content: Text(ErrorUtils.sanitize(_error)),
            leading: const Icon(Icons.wifi_off, color: AppColors.warning),
            actions: [
              TextButton(onPressed: _loadFund, child: const Text('إعادة المحاولة')),
            ],
            backgroundColor: AppColors.warningContainer,
          ),
        Expanded(child: SingleChildScrollView(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _headerCard(),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        _dateButton('من', _startDate, () => _pickDate(isStart: true)),
                        const SizedBox(width: 8),
                        _dateButton('إلى', _endDate, () => _pickDate(isStart: false)),
                        const SizedBox(width: 8),
                        AppButton(
                          label: 'عرض الحركات',
                          icon: Icons.search,
                          onPressed: _loadLedger,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (_isLoadingLedger)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 48),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_ledger.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 48),
                  child: Center(child: Text('لا توجد حركات لهذا الصندوق')),
                )
              else
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    columnSpacing: 16,
                    columns: const [
                      DataColumn(label: Text('التاريخ')),
                      DataColumn(label: Text('النوع')),
                      DataColumn(label: Text('البيان')),
                      DataColumn(label: Text('المبلغ')),
                      DataColumn(label: Text('الرصيد بعد الحركة')),
                      DataColumn(label: Text('العملة')),
                    ],
                    rows: _ledger.map((row) {
                      final amount = parseMoney(row['amount']) ?? Decimal.zero;
                      final balanceAfter = parseMoney(row['balance_after'] ?? row['balance']) ?? Decimal.zero;
                      return DataRow(cells: [
                        DataCell(Text(row['date']?.toString() ?? '')),
                        DataCell(_typeBadge(row['type']?.toString() ?? '')),
                        DataCell(SizedBox(
                          width: 200,
                          child: Text(row['description']?.toString() ?? '', overflow: TextOverflow.ellipsis),
                        )),
                        DataCell(Text(
                          amount.toStringAsFixed(2),
                          style: TextStyle(
                            fontWeight: FontWeight.w500,
                            color: amount >= Decimal.zero ? AppColors.success : AppColors.danger,
                          ),
                        )),
                        DataCell(Text(
                          balanceAfter.toStringAsFixed(2),
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        )),
                        DataCell(Text(row['currency']?.toString() ?? '')),
                      ]);
                    }).toList(),
                  ),
                ),
            ],
          ),
        )),
      ],
    );
  }

  Widget _headerCard() {
    final fund = _fund ?? {};
    final fundType = fund['fund_type']?.toString() ?? 'main';
    final fundTypeLabel = switch (fundType) {
      'sub' => 'فرعي',
      'project' => 'مشروع',
      _ => 'رئيسي',
    };
    final currency = fund['currency']?.toString() ?? CurrencyHelper.baseCurrency;
    final balance = _balance ?? parseMoney(fund['balance'] ?? fund['current_balance'] ?? '');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                  child: Icon(Icons.account_balance_wallet, color: Theme.of(context).colorScheme.primary),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        fund['name']?.toString() ?? widget.fundName,
                        style: AppTextStyles.headlineSmall,
                      ),
                      if (fund['code'] != null)
                        Text('الرمز: ${fund['code']}', style: AppTextStyles.bodySmall),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            Row(
              children: [
                _headerItem('النوع', fundTypeLabel),
                _headerItem('العملة', currency),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(AppDimens.radiusCard),
              ),
              child: Column(
                children: [
                  Text('الرصيد الحالي', style: AppTextStyles.bodyMedium),
                  const SizedBox(height: 4),
                  Text(
                    balance != null ? '${balance.toStringAsFixed(2)} $currency' : '—',
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: balance != null && balance < Decimal.zero ? AppColors.danger : AppColors.success,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _headerItem(String label, String value) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTextStyles.bodySmall),
          const SizedBox(height: 2),
          Text(value, style: AppTextStyles.titleSmall),
        ],
      ),
    );
  }

  Widget _typeBadge(String type) {
    String label;
    Color color;
    switch (type) {
      case 'deposit':
        label = 'إيداع';
        color = AppColors.success;
        break;
      case 'withdraw':
        label = 'سحب';
        color = AppColors.danger;
        break;
      case 'transfer':
        label = 'تحويل';
        color = AppColors.secondary;
        break;
      default:
        label = type;
        color = AppColors.buttonCancel;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.bold,
          fontSize: 12,
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
