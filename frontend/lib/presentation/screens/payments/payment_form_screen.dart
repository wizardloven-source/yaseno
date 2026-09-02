import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../widgets/app_widgets.dart';

class PaymentFormScreen extends StatefulWidget {
  final String? paymentId;
  final bool readOnly;

  const PaymentFormScreen({super.key, this.paymentId, this.readOnly = false});

  @override
  State<PaymentFormScreen> createState() => _PaymentFormScreenState();
}

class _PaymentFormScreenState extends State<PaymentFormScreen> {
  final ApiService _api = ApiService();
  final _formKey = GlobalKey<FormState>();
  final _amountController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _counterpartyController = TextEditingController();
  String _paymentType = 'receive';
  String _paymentMethod = 'cash';
  String _currency = 'USD';
  bool _isSaving = false;
  Map<String, dynamic>? _paymentData;
  bool _isLoading = false;

  String? _selectedFundId;
  List<Map<String, dynamic>> _funds = [];

  String? _selectedInvoiceId;
  List<Map<String, dynamic>> _invoices = [];

  List<Map<String, dynamic>> _allocations = [];
  final _allocationController = TextEditingController();
  bool _isAllocating = false;

  Decimal get _paymentAmount => _paymentData != null
      ? parseMoney(_paymentData!['amount']) ?? Decimal.zero
      : Decimal.zero;

  Decimal get _allocatedTotal => _allocations.fold(
      Decimal.zero, (sum, a) => sum + (parseMoney(a['amount']) ?? Decimal.zero));

  Decimal get _remainingToAllocate => _paymentAmount - _allocatedTotal;

  List<Map<String, dynamic>> _currencies = [];

  bool get _isEdit => widget.paymentId != null;

  @override
  void initState() {
    super.initState();
    _loadFunds();
    _loadInvoices();
    _loadCurrencies();
    if (_isEdit) _loadPayment();
  }

  Future<void> _loadFunds() async {
    try {
      final response = await _api.get('funds');
      final items = response['items'] ?? response['data'] ?? [];
      if (mounted && items is List) {
        setState(() {
          _funds = items.cast<Map<String, dynamic>>();
        });
      }
    } catch (e) {
      // silent fail, funds dropdown will be empty
    }
  }

  Future<void> _loadInvoices() async {
    try {
      final response = await _api.get('invoices', queryParameters: {'status': 'posted'});
      final items = response['items'] ?? response['data'] ?? [];
      if (mounted && items is List) {
        setState(() {
          _invoices = items.cast<Map<String, dynamic>>();
        });
      }
    } catch (e) {
      // silent fail, invoices dropdown will be empty
    }
  }

  Future<void> _loadCurrencies() async {
    await CurrencyHelper.load();
    if (mounted) {
      setState(() {
        _currencies = CurrencyHelper.currencies;
        if (_currencies.isNotEmpty && !_currencies.any((c) => c['code'] == _currency)) {
          _currency = CurrencyHelper.baseCurrency;
        }
      });
    }
  }

  Future<void> _loadPayment() async {
    setState(() => _isLoading = true);
    try {
      final response = await _api.getPayment(widget.paymentId!);
      final data = response['data'] ?? response;
      setState(() {
        _paymentData = data;
        _paymentType = data['payment_type'] ?? 'receive';
        _paymentMethod = data['payment_method'] ?? 'cash';
        _amountController.text = formatMoney(data['amount']);
        _descriptionController.text = data['notes'] ?? data['description'] ?? '';
        _currency = data['currency'] ?? CurrencyHelper.baseCurrency;
        _selectedFundId = data['fund_id'];
        _selectedInvoiceId = data['invoice_id'];
        _counterpartyController.text = data['counterparty_name'] ?? '';
        _allocations = _extractAllocations(data);
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSaving = true);
    try {
      final amount = parseMoney(_amountController.text) ?? Decimal.zero;
      final data = <String, dynamic>{
        'payment_type': _paymentType,
        'payment_method': _paymentMethod,
        'amount': amount.toDouble(),
        'currency': _currency,
        'fund_id': _selectedFundId ?? 'default',
        'description': _descriptionController.text.trim().isNotEmpty ? _descriptionController.text.trim() : null,
      };
      if (_selectedInvoiceId != null) {
        data['invoice_id'] = _selectedInvoiceId;
      }
      if (_counterpartyController.text.trim().isNotEmpty) {
        data['counterparty_name'] = _counterpartyController.text.trim();
      }
      if (_isEdit) {
        await _api.put('payments/${widget.paymentId}', data: data);
      } else {
        await _api.post('payments', data: data);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم إنشاء الدفع بنجاح'), backgroundColor: AppColors.success),
        );
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _completePayment() async {
    try {
      await _api.post('payments/${widget.paymentId}/submit');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم إكمال الدفع بنجاح'), backgroundColor: AppColors.success),
        );
        _loadPayment();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    }
  }

  Future<void> _cancelPayment() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('إلغاء الدفع'),
        content: const Text('هل أنت متأكد من إلغاء هذا الدفع؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('لا')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('نعم', style: TextStyle(color: AppColors.danger))),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _api.cancelPayment(widget.paymentId!);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم إلغاء الدفع'), backgroundColor: AppColors.warning),
        );
        _loadPayment();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    }
  }

  List<Map<String, dynamic>> _extractAllocations(dynamic data) {
    if (data is! Map) return [];
    final raw = data['allocations'] ??
        data['allocation_details'] ??
        data['allocations_list'];
    if (raw is List) {
      return raw.cast<Map<String, dynamic>>();
    }
    return [];
  }

  Future<void> _allocate() async {
    if (_selectedInvoiceId == null) return;
    final amount = parseMoney(_allocationController.text);
    if (amount == null || amount <= Decimal.zero) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('أدخل مبلغ تخصيص صحيح')),
      );
      return;
    }
    if (amount > _remainingToAllocate) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('المبلغ أكبر من المبلغ المتبقي للتخصيص')),
      );
      return;
    }
    setState(() => _isAllocating = true);
    try {
      await _api.post('payments/${widget.paymentId}/allocate', data: {
        'invoice_id': _selectedInvoiceId,
        'amount': amount.toDouble(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم تخصيص الدفعة بنجاح'),
            backgroundColor: AppColors.success,
          ),
        );
        _allocationController.clear();
        _loadPayment();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _isAllocating = false);
    }
  }

  Widget _buildAllocationRow(Map<String, dynamic> allocation) {
    final amount = parseMoney(allocation['amount']) ?? Decimal.zero;
    final invoiceNo = (allocation['invoice_number'] ??
            allocation['invoice_no'] ??
            allocation['invoice'] ??
            '')
        .toString();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            invoiceNo.isNotEmpty ? 'الفاتورة: $invoiceNo' : 'تخصيص',
            style: const TextStyle(fontSize: 12),
          ),
          Text(
            formatMoneyCurrency(amount, currency: _currency),
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _amountController.dispose();
    _descriptionController.dispose();
    _counterpartyController.dispose();
    _allocationController.dispose();
    super.dispose();
  }

  String _statusLabel(String? status) {
    switch (status) {
      case 'draft': return 'مسودة';
      case 'pending': return 'بانتظار الاعتماد';
      case 'approved': return 'معتمد';
      case 'completed': return 'مكتمل';
      case 'rejected': return 'مرفوض';
      case 'cancelled': return 'ملغي';
      default: return status ?? '';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.readOnly
            ? 'تفاصيل الدفع'
            : (_isEdit ? 'تعديل الدفع' : 'دفع جديد')),
        centerTitle: true,
        actions: [
          if (widget.readOnly && _paymentData != null) ...[
            if (_paymentData!['status'] == 'draft')
              TextButton.icon(
                onPressed: _completePayment,
                icon: const Icon(Icons.check, color: AppColors.success),
                label: const Text('إكمال', style: TextStyle(color: AppColors.success)),
              ),
            if (_paymentData!['status'] != 'cancelled' && _paymentData!['status'] != 'completed')
              TextButton.icon(
                onPressed: _cancelPayment,
                icon: const Icon(Icons.cancel, color: AppColors.danger),
                label: const Text('إلغاء', style: TextStyle(color: AppColors.danger)),
              ),
          ],
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (_paymentData != null) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            const Text('الحالة: ', style: TextStyle(fontWeight: FontWeight.bold)),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                              decoration: BoxDecoration(
                                color: AppColors.secondaryContainer,
                                borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                              ),
                              child: Text(_statusLabel(_paymentData!['status']),
                                  style: const TextStyle(color: AppColors.secondary, fontWeight: FontWeight.bold)),
                            ),
                            const SizedBox(width: 16),
                            Text('الكود: ${_paymentData!['code'] ?? ''}'),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    DropdownButtonFormField<String>(
                      value: _paymentType,
                      decoration: const InputDecoration(labelText: 'نوع الدفع', border: OutlineInputBorder()),
                      items: const [
                        DropdownMenuItem(value: 'receive', child: Text('قبض')),
                        DropdownMenuItem(value: 'pay', child: Text('صرف')),
                        DropdownMenuItem(value: 'transfer', child: Text('تحويل')),
                      ],
                      onChanged: widget.readOnly ? null : (v) => setState(() => _paymentType = v!),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _paymentMethod,
                      decoration: const InputDecoration(labelText: 'طريقة الدفع', border: OutlineInputBorder()),
                      items: const [
                        DropdownMenuItem(value: 'cash', child: Text('نقدي')),
                        DropdownMenuItem(value: 'check', child: Text('شيك')),
                        DropdownMenuItem(value: 'transfer', child: Text('تحويل بنكي')),
                      ],
                      onChanged: widget.readOnly ? null : (v) => setState(() => _paymentMethod = v!),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _selectedFundId,
                      decoration: const InputDecoration(labelText: 'الصندوق', border: OutlineInputBorder()),
                      hint: const Text('اختر الصندوق'),
                      items: [
                        const DropdownMenuItem(value: null, child: Text('الصندوق الافتراضي')),
                        ..._funds.map((fund) => DropdownMenuItem(
                          value: fund['id']?.toString(),
                          child: Text(fund['name'] ?? fund['code'] ?? 'صندوق'),
                        )),
                      ],
                      onChanged: widget.readOnly ? null : (v) => setState(() => _selectedFundId = v),
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _amountController,
                      decoration: InputDecoration(labelText: 'المبلغ', border: const OutlineInputBorder(), prefixText: '$_currency '),
                      keyboardType: TextInputType.number,
                      enabled: !widget.readOnly && !_isEdit,
                      validator: (v) {
                        if (v == null || v.isEmpty) return 'مطلوب';
                        if (parseMoney(v) == null ||
                            parseMoneyOrZero(v) <= Decimal.zero) {
                          return 'أدخل مبلغ صحيح';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _currency,
                      decoration: const InputDecoration(labelText: 'العملة', border: OutlineInputBorder()),
                      items: _currencies.map((c) => DropdownMenuItem<String>(
                        value: (c['code'] ?? c['id']?.toString() ?? '').toString(),
                        child: Text(c['name'] ?? c['code'] ?? ''),
                      )).toList(),
                      onChanged: widget.readOnly ? null : (v) => setState(() => _currency = v!),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _selectedInvoiceId,
                      decoration: const InputDecoration(labelText: 'فاتورة مرتبطة (اختياري)', border: OutlineInputBorder()),
                      hint: const Text('اختر فاتورة'),
                      isExpanded: true,
                      items: [
                        const DropdownMenuItem(value: null, child: Text('بدون فاتورة')),
                        ..._invoices.map((inv) {
                          final code = inv['invoice_number'] ?? inv['code'] ?? inv['number'] ?? '';
                          final amount = parseMoney(inv['total'] ?? inv['total_amount'] ?? inv['amount']) ??
                              Decimal.zero;
                          final currency = (inv['currency'] ?? CurrencyHelper.baseCurrency).toString();
                          return DropdownMenuItem(
                            value: inv['id']?.toString(),
                            child: Text(
                              '$code - ${formatMoneyCurrency(amount, currency: currency)}',
                              overflow: TextOverflow.ellipsis,
                            ),
                          );
                        }),
                      ],
                      onChanged: widget.readOnly ? null : (v) => setState(() => _selectedInvoiceId = v),
                    ),
                    const SizedBox(height: 16),
                    if (widget.paymentId != null) ...[
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                          border: Border.all(color: AppColors.secondaryContainer),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.call_split, size: 18, color: AppColors.secondary),
                                const SizedBox(width: 8),
                                const Text('توزيع الدفعة', style: AppTextStyles.titleMedium),
                                const Spacer(),
                                Text(
                                  formatMoneyCurrency(_remainingToAllocate,
                                      currency: _currency),
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.secondary,
                                  ),
                                ),
                              ],
                            ),
                            if (_allocations.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              ..._allocations.map((a) => _buildAllocationRow(a)),
                              const Divider(height: 16),
                            ],
                            const SizedBox(height: 8),
                            if (_selectedInvoiceId != null)
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: _allocationController,
                                      keyboardType: TextInputType.number,
                                      decoration: InputDecoration(
                                        labelText: 'مبلغ التخصيص',
                                        border: const OutlineInputBorder(),
                                        prefixText: '$_currency ',
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  AppButton(
                                    label: 'تخصيص',
                                    icon: Icons.check,
                                    variant: AppButtonVariant.success,
                                    loading: _isAllocating,
                                    onPressed: _allocate,
                                  ),
                                ],
                              )
                            else
                              const Text('اختر فاتورة لتوزيع الدفعة عليها', style: TextStyle(fontSize: 12, color: AppColors.textHint)),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    TextFormField(
                      controller: _counterpartyController,
                      decoration: const InputDecoration(labelText: 'اسم العميل/المورد (اختياري)', border: OutlineInputBorder()),
                      enabled: !widget.readOnly,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _descriptionController,
                      decoration: const InputDecoration(labelText: 'الوصف', border: OutlineInputBorder()),
                      enabled: !widget.readOnly,
                      maxLines: 2,
                    ),
                    const SizedBox(height: 24),
                    if (!widget.readOnly)
                      AppButton(
                        label: 'حفظ الدفع',
                        icon: Icons.save,
                        variant: AppButtonVariant.success,
                        loading: _isSaving,
                        expanded: true,
                        onPressed: _save,
                      ),
                  ],
                ),
              ),
            ),
    );
  }
}
