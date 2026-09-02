import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../presentation/widgets/app_widgets.dart';

class CurrenciesScreen extends StatefulWidget {
  const CurrenciesScreen({super.key});

  @override
  State<CurrenciesScreen> createState() => _CurrenciesScreenState();
}

class _CurrenciesScreenState extends State<CurrenciesScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _currencies = [];
  bool _isLoading = true;
  String? _error;

  String? _baseCurrencyCode;
  String _searchText = '';

  final _codeController = TextEditingController();
  final _nameController = TextEditingController();
  final _symbolController = TextEditingController();
  final _decimalPlacesController = TextEditingController(text: '2');

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _codeController.dispose();
    _nameController.dispose();
    _symbolController.dispose();
    _decimalPlacesController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('currency');
      final items = (response['items'] ?? []) as List;

      String? baseCode;
      try {
        final baseRes = await _api.get('currency/base');
        baseCode = baseRes is Map ? baseRes['code'] as String? : null;
      } catch (_) {}

      setState(() {
        _currencies = items.cast<Map<String, dynamic>>();
        _baseCurrencyCode = baseCode;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  void _showCurrencyDialog({Map<String, dynamic>? currency}) {
    final isEdit = currency != null;
    _codeController.text = currency?['code'] ?? '';
    _nameController.text = currency?['name'] ?? '';
    _symbolController.text = currency?['symbol'] ?? '';
    _decimalPlacesController.text =
        (currency?['decimal_places'] ?? 2).toString();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(isEdit ? 'تعديل العملة' : 'إضافة عملة'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _codeController,
                decoration: const InputDecoration(
                  labelText: 'الرمز',
                  hintText: 'مثال: USD',
                ),
                textCapitalization: TextCapitalization.characters,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'الاسم',
                  hintText: 'مثال: دولار أمريكي',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _symbolController,
                decoration: const InputDecoration(
                  labelText: 'الرمز الرمزي',
                  hintText: 'مثال: \$',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _decimalPlacesController,
                decoration: const InputDecoration(
                  labelText: 'اماكن الكسور العشرية',
                ),
                keyboardType: TextInputType.number,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
            child: const Text('إلغاء'),
          ),
          AppButton(
            label: 'حفظ',
            variant: AppButtonVariant.success,
            onPressed: () => _saveCurrency(ctx, currency?['id']),
          ),
        ],
      ),
    );
  }

  Future<void> _saveCurrency(BuildContext dialogContext, String? id) async {
    final data = {
      'code': _codeController.text.trim(),
      'name': _nameController.text.trim(),
      'symbol': _symbolController.text.trim(),
      'decimal_places': int.tryParse(_decimalPlacesController.text) ?? 2,
    };

    if ((data['code'] ?? '').toString().isEmpty || (data['name'] ?? '').toString().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('الرمز والاسم مطلوبان')),
      );
      return;
    }

    try {
      final response = id != null
          ? await _api.put('currency/$id', data: data)
          : await _api.post('currency', data: data);
      Navigator.pop(dialogContext);
      _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Future<void> _deleteCurrency(String id, String code) async {
    if (code == _baseCurrencyCode) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('لا يمكن حذف العملة الأساسية'), backgroundColor: AppColors.warning),
        );
      }
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف العملة'),
        content: Text('هل أنت متأكد من حذف العملة "$code"؟\nقد تتأثر الفواتير والمبيعات المرتبطة بهذه العملة.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
              child: const Text('إلغاء')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('حذف', style: TextStyle(color: AppColors.danger))),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final res = await _api.delete('currency/$id');
      _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  Future<void> _setAsBase(String id) async {
    try {
      await _api.post('currency/$id/base');
      _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  void _showExchangeRateDialog() {
    String? fromCode;
    String? toCode;
    final rateController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('أسعار الصرف'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  value: fromCode,
                  decoration: const InputDecoration(labelText: 'من عملة'),
                  items: _currencies
                      .map((c) => DropdownMenuItem(
                            value: c['code'] as String,
                            child: Text('${c['code']} - ${c['name']}'),
                          ))
                      .toList(),
                  onChanged: (v) => setDialogState(() => fromCode = v),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: toCode,
                  decoration: const InputDecoration(labelText: 'إلى عملة'),
                  items: _currencies
                      .map((c) => DropdownMenuItem(
                            value: c['code'] as String,
                            child: Text('${c['code']} - ${c['name']}'),
                          ))
                      .toList(),
                  onChanged: (v) => setDialogState(() => toCode = v),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: rateController,
                  decoration: const InputDecoration(labelText: 'السعر'),
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
              child: const Text('إلغاء'),
            ),
            if (fromCode != null && toCode != null)
              TextButton(
                onPressed: () async {
                  try {
                    final res = await _api.get(
                      'currency/exchange-rate',
                      queryParameters: {
                        'from_currency_code': fromCode,
                        'to_currency_code': toCode,
                      },
                    );
                    final rateData = res['data'];
                    final rate = rateData is Map
                        ? (rateData['rate'] ?? rateData['exchange_rate'] ?? '')
                        : '';
                    setDialogState(() {
                      rateController.text = rate.toString();
                    });
                  } catch (e) {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(ErrorUtils.sanitize(e))));
                    }
                  }
                },
                child: const Text('استرجاع'),
              ),
            AppButton(
              label: 'حفظ السعر',
              variant: AppButtonVariant.success,
              onPressed: () async {
                if (fromCode == null || toCode == null) return;
                final rate = parseMoney(rateController.text);
                if (rate == null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('أدخل سعرًا صحيحًا')),
                  );
                  return;
                }
                try {
                  final currency = _currencies.firstWhere(
                    (c) => c['code'] == fromCode,
                  );
                  final res = await _api.post(
                    'currency/${currency['id']}/exchange-rate',
                    data: {
                      'target_currency_code': toCode,
                      'rate': rate.toString(),
                    },
                  );
                  if (res['success'] == false) {
                    throw Exception(res['message'] ?? 'فشل حفظ سعر الصرف');
                  }
                  Navigator.pop(ctx);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('تم حفظ سعر الصرف')),
                  );
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(ErrorUtils.sanitize(e))));
                  }
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  void _showRevaluationDialog() {
    DateTime asOfDate = DateTime.now();
    final gainController = TextEditingController();
    final lossController = TextEditingController();
    bool submitting = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('تقييم العملة'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                OutlinedButton.icon(
                  onPressed: () async {
                    final picked = await showDatePicker(
                      context: context,
                      initialDate: asOfDate,
                      firstDate: DateTime(2020),
                      lastDate: DateTime(2030),
                    );
                    if (picked != null) {
                      setDialogState(() => asOfDate = picked);
                    }
                  },
                  icon: const Icon(Icons.calendar_today, size: 18),
                  label: Text(
                      'تاريخ التقييم: ${DateFormat('yyyy-MM-dd').format(asOfDate)}'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: gainController,
                  decoration: const InputDecoration(
                    labelText: 'حساب أرباح فروق العملة (fx_gain_account_code)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: lossController,
                  decoration: const InputDecoration(
                    labelText: 'حساب خسائر فروق العملة (fx_loss_account_code)',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
              child: const Text('إلغاء'),
            ),
            AppButton(
              label: 'تنفيذ',
              variant: AppButtonVariant.success,
              loading: submitting,
              onPressed: submitting
                  ? null
                  : () async {
                      final gain = gainController.text.trim();
                      final loss = lossController.text.trim();
                      if (gain.isEmpty || loss.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                              content: Text('أدخل حسابات الأرباح والخسائر')),
                        );
                        return;
                      }
                      setDialogState(() => submitting = true);
                      try {
                        final res = await _api.post('currency/revaluation',
                            data: {
                              'as_of_date':
                                  DateFormat('yyyy-MM-dd').format(asOfDate),
                              'fx_gain_account_code': gain,
                              'fx_loss_account_code': loss,
                            });
                        final data = res['data'] ?? res;
                        if (ctx.mounted) {
                          showDialog(
                            context: ctx,
                            builder: (resultCtx) => AlertDialog(
                              title: const Text('نتيجة التقييم'),
                              content: SingleChildScrollView(
                                child: _buildRevaluationResult(data),
                              ),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.pop(resultCtx),
                                  style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
                                  child: const Text('حسناً'),
                                ),
                              ],
                            ),
                          );
                        }
                      } catch (e) {
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                              content: Text(ErrorUtils.sanitize(e))));
                        }
                      } finally {
                        if (ctx.mounted) {
                          setDialogState(() => submitting = false);
                          Navigator.pop(ctx);
                        }
                      }
                    },
            ),
            ],
          ),
        ),
    );
  }

  Widget _buildRevaluationResult(dynamic data) {
    if (data is! Map) {
      return Text('$data');
    }
    final rows = <Widget>[];
    final totalGain = parseMoney(data['total_gain'] ?? data['total_gains']) ?? Decimal.zero;
    final totalLoss = parseMoney(data['total_loss'] ?? data['total_losses']) ?? Decimal.zero;
    if (totalGain != Decimal.zero) {
      rows.add(_resultRow('إجمالي الأرباح', totalGain, AppColors.success));
    }
    if (totalLoss != Decimal.zero) {
      rows.add(_resultRow('إجمالي الخسائر', totalLoss, AppColors.danger));
    }
    final items = data['items'];
    if (items is List && items.isNotEmpty) {
      rows.add(const Divider());
      for (final item in items) {
        if (item is Map) {
          final code = item['account_code'] ?? item['code'] ?? '';
          final name = item['name'] ?? '';
          final gain = parseMoney(item['gain'] ?? item['gain_amount']) ?? Decimal.zero;
          final loss = parseMoney(item['loss'] ?? item['loss_amount']) ?? Decimal.zero;
          if (gain != Decimal.zero) {
            rows.add(_resultRow('${code.isNotEmpty ? '$code - ' : ''}$name (ربح)', gain, AppColors.success));
          }
          if (loss != Decimal.zero) {
            rows.add(_resultRow('${code.isNotEmpty ? '$code - ' : ''}$name (خسارة)', loss, AppColors.danger));
          }
        }
      }
    }
    if (rows.isEmpty) {
      rows.add(const Text('لا توجد نتائج'));
    }
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: rows,
    );
  }

  Widget _resultRow(String label, Decimal value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(child: Text(label)),
          Text(formatMoney(value),
              style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: color)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('إدارة العملات'),
        centerTitle: true,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              onChanged: (v) => setState(() => _searchText = v),
              decoration: InputDecoration(
                hintText: 'بحث بالرمز أو الاسم...',
                prefixIcon: const Icon(Icons.search, size: 20),
                suffixIcon: _searchText.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 20),
                        onPressed: () => setState(() => _searchText = ''),
                      )
                    : null,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppDimens.radiusInput)),
                filled: true,
                fillColor: Theme.of(context).colorScheme.surface,
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                isDense: true,
              ),
            ),
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.published_with_changes),
            onPressed: _showRevaluationDialog,
            tooltip: 'تقييم العملة',
          ),
          IconButton(
            icon: const Icon(Icons.currency_exchange),
            onPressed: _showExchangeRateDialog,
            tooltip: 'أسعار الصرف',
          ),
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
          Expanded(child: _buildBody()),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCurrencyDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_currencies.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.currency_exchange, size: 64, color: AppColors.textSecondary),
            SizedBox(height: 16),
            Text('لا توجد عملات',
                style: TextStyle(fontSize: 18, color: AppColors.textMuted)),
          ],
        ),
      );
    }
    var filtered = _currencies;
    if (_searchText.isNotEmpty) {
      final q = _searchText.toLowerCase();
      filtered = filtered.where((c) =>
        (c['code'] ?? '').toString().toLowerCase().contains(q) ||
        (c['name'] ?? '').toString().toLowerCase().contains(q)
      ).toList();
    }
    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: filtered.length,
        itemBuilder: (context, index) {
          final currency = filtered[index];
          final isBase = currency['code'] == _baseCurrencyCode ||
              currency['is_base'] == true;
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: isBase
                    ? AppColors.primaryContainer
                    : AppColors.secondaryContainer,
                child: Text(
                  currency['symbol'] ?? '',
                  style: TextStyle(
                    color: isBase ? AppColors.primary : AppColors.secondary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              title: Row(
                children: [
                  Text('${currency['name'] ?? ''}',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  if (isBase) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                      ),
                      child: const Text('أساسية',
                          style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: Colors.white)),
                    ),
                  ],
                ],
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('الرمز: ${currency['code'] ?? ''}'),
                  Text(
                      'الاماكن العشرية: ${currency['decimal_places'] ?? 2}'),
                ],
              ),
              trailing: PopupMenuButton(
                itemBuilder: (ctx) => [
                  const PopupMenuItem(
                      value: 'edit', child: Text('تعديل')),
                  if (!isBase)
                    const PopupMenuItem(
                        value: 'base', child: Text('تعيين كأساسية')),
                  const PopupMenuItem(
                      value: 'delete',
                      child: Text('حذف',
                          style: TextStyle(color: AppColors.danger))),
                ],
                onSelected: (v) {
                  if (v == 'edit') {
                    _showCurrencyDialog(currency: currency);
                  } else if (v == 'base') {
                    _setAsBase(currency['id']);
                  } else if (v == 'delete') {
                    _deleteCurrency(currency['id'], currency['code'] ?? '');
                  }
                },
              ),
            ),
          );
        },
      ),
    );
  }
}
