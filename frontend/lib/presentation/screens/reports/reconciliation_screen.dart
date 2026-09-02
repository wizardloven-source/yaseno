import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';

class ReconciliationScreen extends StatefulWidget {
  const ReconciliationScreen({super.key});

  @override
  State<ReconciliationScreen> createState() => _ReconciliationScreenState();
}

class _ReconciliationScreenState extends State<ReconciliationScreen> {
  final ApiService _api = ApiService();

  List<Map<String, dynamic>> _funds = [];
  List<Map<String, dynamic>> _reconciliations = [];
  bool _isLoading = true;
  bool _isSubmitting = false;
  String? _error;

  String? _selectedFundId;
  DateTime _asOfDate = DateTime.now();
  final _openingController = TextEditingController();
  final _statementController = TextEditingController();
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

  @override
  void dispose() {
    _openingController.dispose();
    _statementController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final fundsResponse = await _api.get('funds');
      final fundsData = fundsResponse['data'] ?? fundsResponse;
      final funds = (fundsData is Map ? fundsData['items'] : fundsData) ?? [];

      final reconResponse = await _api.get('reconciliations');
      final reconData = reconResponse['data'] ?? reconResponse;
      final recons = (reconData is Map ? reconData['items'] : reconData) ?? [];

      setState(() {
        _funds = (funds as List).cast<Map<String, dynamic>>();
        _reconciliations = (recons as List).cast<Map<String, dynamic>>();
        if (_selectedFundId == null && _funds.isNotEmpty) {
          _selectedFundId = _funds.first['id'].toString();
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

  String? _fundName(String? id) {
    if (id == null) return null;
    for (final f in _funds) {
      if (f['id'].toString() == id.toString()) {
        final name = f['name'] ?? '';
        final code = f['code'] ?? '';
        return name.isNotEmpty ? '$name${code.isNotEmpty ? ' ($code)' : ''}' : '$code';
      }
    }
    return id;
  }

  Future<void> _pickAsOfDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _asOfDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() => _asOfDate = picked);
    }
  }

  Future<void> _startReconciliation() async {
    if (_selectedFundId == null) {
      _showSnack('اختر صندوقًا أولاً');
      return;
    }
    final statementBalance = parseMoney(_statementController.text.trim());
    if (statementBalance == null) {
      _showSnack('أدخل رصيد كشف الحساب');
      return;
    }
    setState(() => _isSubmitting = true);
    try {
      await _api.post('reconciliations', data: {
        'fund_id': _selectedFundId,
        'as_of_date': DateFormat('yyyy-MM-dd').format(_asOfDate),
        'statement_balance': statementBalance,
        'opening_balance':
            parseMoney(_openingController.text.trim()) ?? Decimal.zero,
      });
      if (mounted) {
        _openingController.clear();
        _statementController.clear();
        _showSnack('تم بدء المطابقة بنجاح', isError: false);
      }
      await _loadData();
    } catch (e) {
      _showSnack(ErrorUtils.sanitize(e));
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  void _showSnack(String message, {bool isError = true}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: isError ? AppColors.danger : AppColors.success,
    ));
  }

  String _statusLabel(String? status) {
    switch (status) {
      case 'open':
      case 'in_progress':
        return 'قيد التنفيذ';
      case 'completed':
        return 'مكتملة';
      case 'matched':
        return 'مطابقة';
      case 'draft':
        return 'مسودة';
      default:
        return status ?? '-';
    }
  }

  Color _statusColor(String? status) {
    switch (status) {
      case 'completed':
      case 'matched':
        return AppColors.success;
      case 'open':
      case 'in_progress':
      case 'draft':
        return AppColors.warning;
      default:
        return AppColors.textHint;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('المطابقة البنكية'),
        centerTitle: true,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
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
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : ListView(
                    padding: const EdgeInsets.all(AppDimens.s2),
                    children: [
                      _buildNewReconciliationCard(),
                      const SizedBox(height: 16),
                      Text('المطابقات السابقة',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      if (_reconciliations.isEmpty)
                        const Center(child: Text('لا توجد مطابقات'))
                      else
                        ..._reconciliations.map(_buildReconciliationCard),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildNewReconciliationCard() {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimens.radiusCard)),
      child: Padding(
        padding: const EdgeInsets.all(AppDimens.s3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('مطابقة جديدة',
                style: AppTextStyles.titleMedium),
            const Divider(),
            DropdownButtonFormField<String>(
              value: _selectedFundId,
              decoration: const InputDecoration(
                labelText: 'الصندوق / البنك',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.account_balance),
              ),
              items: _funds
                  .map((f) => DropdownMenuItem(
                        value: f['id'].toString(),
                        child: Text(_fundName(f['id'].toString()) ?? ''),
                      ))
                  .toList(),
              onChanged: (v) => setState(() => _selectedFundId = v),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _pickAsOfDate,
              icon: const Icon(Icons.calendar_today, size: 18),
              label: Text('تاريخ المطابقة: ${DateFormat('yyyy-MM-dd').format(_asOfDate)}'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _openingController,
              decoration: const InputDecoration(
                labelText: 'الرصيد الافتتاحي',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.trending_up),
              ),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _statementController,
              decoration: const InputDecoration(
                labelText: 'رصيد كشف الحساب',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.description),
              ),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
            const SizedBox(height: 16),
            AppButton(
              onPressed: _isSubmitting ? null : _startReconciliation,
              icon: Icons.play_arrow,
              loading: _isSubmitting,
              label: 'بدء مطابقة',
              expanded: true,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReconciliationCard(Map<String, dynamic> recon) {
    final status = (recon['status'] ?? '').toString();
    final variance = recon['variance'];
    final fundId = (recon['fund_id'] ?? recon['fundId'] ?? '').toString();
    final dateStr = (recon['as_of_date'] ?? '').toString();

    return Card(
      margin: const EdgeInsets.only(bottom: AppDimens.s2),
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimens.radiusCard)),
      child: ListTile(
        onTap: () => _openDetail(recon),
        leading: CircleAvatar(
          backgroundColor: _statusColor(status).withOpacity(0.1),
          child: Icon(Icons.compare_arrows, color: _statusColor(status)),
        ),
        title: Text(_fundName(fundId) ?? 'صندوق',
            style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (dateStr.isNotEmpty) Text('التاريخ: $dateStr'),
            if (variance != null)
              Text('الفرق: ${formatMoneyCurrency(_num(variance), currency: _currencySymbol)}',
                  style: TextStyle(
                      color: _num(variance) == Decimal.zero ? AppColors.textSecondary : (_num(variance) > Decimal.zero ? AppColors.success : AppColors.danger))),
          ],
        ),
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
  }

  Decimal _num(dynamic v) => parseMoney(v) ?? Decimal.zero;

  void _openDetail(Map<String, dynamic> recon) {
    final id = (recon['id'] ?? '').toString();
    if (id.isEmpty) return;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) => _ReconciliationDetailSheet(
        api: _api,
        reconciliationId: id,
        fundName: _fundName((recon['fund_id'] ?? recon['fundId'] ?? '').toString()) ?? 'صندوق',
      ),
    ).then((_) => _loadData());
  }
}

class _ReconciliationDetailSheet extends StatefulWidget {
  final ApiService api;
  final String reconciliationId;
  final String fundName;

  const _ReconciliationDetailSheet({
    required this.api,
    required this.reconciliationId,
    required this.fundName,
  });

  @override
  State<_ReconciliationDetailSheet> createState() =>
      _ReconciliationDetailSheetState();
}

class _ReconciliationDetailSheetState extends State<_ReconciliationDetailSheet> {
  bool _isLoading = true;
  bool _isCompleting = false;
  String? _error;
  List<Map<String, dynamic>> _items = [];
  String _currencySymbol = 'د.ع';

  @override
  void initState() {
    super.initState();
    _loadDetail();
    _loadCurrency();
  }

  Future<void> _loadCurrency() async {
    try {
      final res = await widget.api.get('currency/base');
      final data = res['data'];
      if (data is Map && mounted) {
        setState(() => _currencySymbol = data['symbol'] ?? 'د.ع');
      }
    } catch (_) {}
  }

  Future<void> _loadDetail() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response =
          await widget.api.get('reconciliations/${widget.reconciliationId}');
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _items = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _toggleMatch(Map<String, dynamic> item, bool matched) async {
    final paymentId = (item['payment_id'] ??
            item['paymentId'] ??
            item['payment'] ??
            item['id'] ??
            '')
        .toString();
    if (paymentId.isEmpty) return;
    setState(() {
      item['matched'] = matched;
      item['is_matched'] = matched;
    });
    try {
      await widget.api.post(
          'reconciliations/${widget.reconciliationId}/match',
          data: {'payment_id': paymentId, 'matched': matched});
    } catch (e) {
      setState(() {
        item['matched'] = !matched;
        item['is_matched'] = !matched;
      });
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Future<void> _complete() async {
    setState(() => _isCompleting = true);
    try {
      final response = await widget.api
          .post('reconciliations/${widget.reconciliationId}/complete');
      final data = response['data'] ?? response;
      final variance = data is Map ? data['variance'] : null;
      if (mounted) {
        await showDialog(
          context: context,
          builder: (ctx) {
            final v = parseMoney(variance) ?? Decimal.zero;
            return AlertDialog(
              title: const Text('إتمام المطابقة'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('تم إتمام المطابقة بنجاح'),
                  const SizedBox(height: 12),
                  Text(
                    'الفرق: ${formatMoneyCurrency(v, currency: _currencySymbol)}',
                    style: AppTextStyles.moneyLarge.copyWith(
                      color: v == Decimal.zero ? AppColors.success : AppColors.warning,
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('حسناً'),
                ),
              ],
            );
          },
        );
        if (mounted) Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    } finally {
      if (mounted) setState(() => _isCompleting = false);
    }
  }

  bool _isMatched(Map<String, dynamic> item) {
    return item['matched'] == true || item['is_matched'] == true;
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: DraggableScrollableSheet(
        initialChildSize: 0.8,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        expand: false,
        builder: (context, scrollController) {
          if (_isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (_error != null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(ErrorUtils.sanitize(_error)),
                  const SizedBox(height: 12),
                  ElevatedButton(
                      onPressed: _loadDetail, child: const Text('إعادة المحاولة')),
                ],
              ),
            );
          }
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Icon(Icons.compare_arrows, color: AppColors.secondary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(widget.fundName,
                          style: AppTextStyles.titleMedium),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: _items.isEmpty
                    ? const Center(child: Text('لا توجد بنود للمطابقة'))
                    : ListView.builder(
                        controller: scrollController,
                        padding: const EdgeInsets.all(8),
                        itemCount: _items.length,
                        itemBuilder: (context, index) {
                          final item = _items[index];
                          final matched = _isMatched(item);
                          final amount = _num(item['amount'] ??
                              item['payment_amount'] ??
                              item['balance']);
                          final ref = (item['payment_reference'] ??
                                  item['reference'] ??
                                  item['description'] ??
                                  item['payment_id'] ??
                                  item['payment'] ??
                                  item['id'] ??
                                  '')
                              .toString();
                          return CheckboxListTile(
                            value: matched,
                            onChanged: (v) => _toggleMatch(item, v ?? false),
                            title: Text(ref.isEmpty ? 'دفعة' : ref,
                                maxLines: 1, overflow: TextOverflow.ellipsis),
                            subtitle: Text(
                                item['payment_date'] != null
                                    ? '${item['payment_date']}'
                                    : ''),
                            secondary: Text(formatMoneyCurrency(amount, currency: _currencySymbol),
                                style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: matched ? AppColors.success : AppColors.textSecondary)),
                          );
                        },
                      ),
              ),
              const Divider(height: 1),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.all(AppDimens.s2),
                  child: AppButton(
                    onPressed: _isCompleting ? null : _complete,
                    icon: Icons.check_circle,
                    loading: _isCompleting,
                    label: 'إتمام المطابقة',
                    expanded: true,
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Decimal _num(dynamic v) => parseMoney(v) ?? Decimal.zero;
}