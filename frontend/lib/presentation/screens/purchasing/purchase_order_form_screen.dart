import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';

class PurchaseOrderFormScreen extends StatefulWidget {
  final String? orderId;
  final bool readOnly;

  const PurchaseOrderFormScreen({super.key, this.orderId, this.readOnly = false});

  @override
  State<PurchaseOrderFormScreen> createState() => _PurchaseOrderFormScreenState();
}

class _PurchaseOrderFormScreenState extends State<PurchaseOrderFormScreen> {
  final ApiService _api = ApiService();
  final _formKey = GlobalKey<FormState>();
  final _supplierNameController = TextEditingController();
  final _notesController = TextEditingController();
  List<_OrderLine> _lines = [];
  bool _isLoading = false;
  bool _isSaving = false;
  String _currency = 'USD';
  Map<String, dynamic>? _orderData;

  bool get _isEdit => widget.orderId != null;

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
    if (_isEdit) _loadOrder();
  }

  Future<void> _loadBaseCurrency() async {
    try {
      final res = await _api.get('currency/base');
      final data = res['data'];
      if (data is Map && mounted) {
        setState(() => _currency = data['code'] ?? 'USD');
      }
    } catch (_) {}
  }

  Future<void> _loadOrder() async {
    setState(() => _isLoading = true);
    try {
      final response = await _api.getPurchaseOrder(widget.orderId!);
      final data = response['data'] ?? response;
      setState(() {
        _orderData = data;
        _supplierNameController.text = data['supplier_name'] ?? '';
        _notesController.text = data['notes'] ?? '';
        _lines = (data['lines'] as List? ?? []).map((l) => _OrderLine(
          productCode: l['product_code'] ?? '',
          productName: l['product_name'] ?? '',
          quantity: parseMoney(l['quantity']) ?? Decimal.one,
          unitPrice: parseMoney(l['unit_price']) ?? Decimal.zero,
          notes: l['notes'] ?? '',
        )).toList();
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
    if (_lines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('أضف سطراً واحداً على الأقل')));
      return;
    }
    setState(() => _isSaving = true);
    try {
      await _api.createPurchaseOrder({
        'supplier_name': _supplierNameController.text.trim(),
        'currency': _currency,
        'notes': _notesController.text.trim().isNotEmpty ? _notesController.text.trim() : null,
        'lines': _lines.map((l) => {
          'product_code': l.productCode,
          'product_name': l.productName,
          'quantity': l.quantity.toDouble(),
          'unit_price': l.unitPrice.toDouble(),
        }).toList(),
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  void _addLine() {
    setState(() => _lines.add(_OrderLine(
      productCode: '',
      productName: '',
      quantity: Decimal.one,
      unitPrice: Decimal.zero,
    )));
  }

  void _removeLine(int index) {
    setState(() => _lines.removeAt(index));
  }

  Decimal get _totalAmount => _lines.fold(Decimal.zero, (sum, l) => sum + l.quantity * l.unitPrice);

  @override
  void dispose() {
    _supplierNameController.dispose();
    _notesController.dispose();
    for (final l in _lines) {
      l.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.readOnly
            ? 'تفاصيل أمر الشراء'
            : (_isEdit ? 'تعديل أمر الشراء' : 'أمر شراء جديد')),
        centerTitle: true,
      ),
      body: _isLoading
          ? const LoadingState(skeleton: false)
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  TextFormField(
                    controller: _supplierNameController,
                    decoration: const InputDecoration(labelText: 'اسم المورد', border: OutlineInputBorder()),
                    enabled: !widget.readOnly,
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'مطلوب' : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _notesController,
                    decoration: const InputDecoration(labelText: 'ملاحظات', border: OutlineInputBorder()),
                    enabled: !widget.readOnly,
                    maxLines: 2,
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      const Text('بنود أمر الشراء', style: AppTextStyles.titleMedium),
                      const Spacer(),
                      if (!widget.readOnly)
                        IconButton(
                          icon: const Icon(Icons.add_circle, color: AppColors.success, size: 30),
                          onPressed: _addLine,
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ..._lines.asMap().entries.map((entry) {
                    final i = entry.key;
                    final line = entry.value;
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(AppDimens.s3),
                        child: Column(
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  flex: 3,
                                  child: TextFormField(
                                    controller: line._codeController,
                                    decoration: const InputDecoration(labelText: 'كود المنتج', border: OutlineInputBorder(), isDense: true),
                                    enabled: !widget.readOnly,
                                    onChanged: (v) => line.productCode = v,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                if (!widget.readOnly)
                                  IconButton(
                                    icon: const Icon(Icons.remove_circle, color: AppColors.danger),
                                    onPressed: () => _removeLine(i),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            TextFormField(
                              controller: line._nameController,
                              decoration: const InputDecoration(labelText: 'اسم المنتج', border: OutlineInputBorder(), isDense: true),
                              enabled: !widget.readOnly,
                              onChanged: (v) => line.productName = v,
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Expanded(
                                  child: TextFormField(
                                    controller: line._qtyController,
                                    decoration: const InputDecoration(labelText: 'الكمية', border: OutlineInputBorder(), isDense: true),
                                    keyboardType: TextInputType.number,
                                    enabled: !widget.readOnly,
                                    onChanged: (v) => line.quantity = parseMoney(v) ?? Decimal.one,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: TextFormField(
                                    controller: line._priceController,
                                    decoration: const InputDecoration(labelText: 'سعر الوحدة', border: OutlineInputBorder(), isDense: true),
                                    keyboardType: TextInputType.number,
                                    enabled: !widget.readOnly,
                                    onChanged: (v) => line.unitPrice = parseMoney(v) ?? Decimal.zero,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Align(
                              alignment: Alignment.centerLeft,
                              child: Text(
                                'الإجمالي: ${formatMoney(line.quantity * line.unitPrice)}',
                                style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.secondary),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                  if (_lines.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(AppDimens.s3),
                      decoration: BoxDecoration(
                        color: AppColors.primaryContainer,
                        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                      ),
                      child: Text(
                        'الإجمالي: ${formatMoneyCurrency(_totalAmount, currency: _currency)}',
                        style: AppTextStyles.moneyLarge,
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),
                  if (!widget.readOnly)
                    AppButton(
                      onPressed: _isSaving ? null : _save,
                      loading: _isSaving,
                      expanded: true,
                      icon: Icons.save,
                      label: 'حفظ أمر الشراء',
                      variant: AppButtonVariant.success,
                    ),
                ],
              ),
            ),
    );
  }
}

class _OrderLine {
  String productCode;
  String productName;
  Decimal quantity;
  Decimal unitPrice;
  String notes;

  final TextEditingController _codeController;
  final TextEditingController _nameController;
  final TextEditingController _qtyController;
  final TextEditingController _priceController;

  _OrderLine({
    required this.productCode,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    this.notes = '',
  })  : _codeController = TextEditingController(text: productCode),
        _nameController = TextEditingController(text: productName),
        _qtyController = TextEditingController(text: quantity.toString()),
        _priceController = TextEditingController(text: unitPrice.toString());

  void dispose() {
    _codeController.dispose();
    _nameController.dispose();
    _qtyController.dispose();
    _priceController.dispose();
  }
}
