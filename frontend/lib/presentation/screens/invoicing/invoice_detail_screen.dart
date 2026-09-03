import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../services/api_service.dart';
import '../../../models/invoicing/invoice_model.dart';
import '../../../data/repositories/product_repository.dart';
import '../../../data/models/product_model.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../utils/currency_helper.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/status_chip.dart';
import 'package:decimal/decimal.dart';

class InvoiceDetailScreen extends StatefulWidget {
  final String invoiceId;

  const InvoiceDetailScreen({super.key, required this.invoiceId});

  @override
  State<InvoiceDetailScreen> createState() => _InvoiceDetailScreenState();
}

class _InvoiceDetailScreenState extends State<InvoiceDetailScreen> {
  final ApiService _api = ApiService();
  InvoiceModel? _invoice;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadInvoice();
  }

  Future<void> _loadInvoice() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('invoices/${widget.invoiceId}');
      final data = response['data'] ?? response;
      setState(() {
        _invoice = InvoiceModel.fromJson(data as Map<String, dynamic>);
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _postInvoice() async {
    try {
      await _api.postInvoice(widget.invoiceId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم ترحيل الفاتورة بنجاح'),
            backgroundColor: AppColors.success,
          ),
        );
        _loadInvoice();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    }
  }

  Future<void> _cancelInvoice() async {
    final reason = await _showReasonDialog('إلغاء الفاتورة');
    if (reason == null) return;
    try {
      await _api.cancelInvoice(widget.invoiceId, reason: reason);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم إلغاء الفاتورة'),
            backgroundColor: AppColors.warning,
          ),
        );
        _loadInvoice();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    }
  }

  Future<void> _returnInvoice() async {
    final reason = await _showReasonDialog('مرتجع الفاتورة');
    if (reason == null) return;
    try {
      await _api.returnInvoice(widget.invoiceId, reason: reason);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم إنشاء المرتجع بنجاح'),
            backgroundColor: AppColors.secondary,
          ),
        );
        _loadInvoice();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    }
  }

  Future<void> _addLine() async {
    final result = await _showLineDialog();
    if (result == null) return;
    try {
      await _api.post('invoices/${widget.invoiceId}/lines', data: {
        'product_code': result['productCode'],
        'product_name': result['productName'],
        'quantity': result['quantity'].toString(),
        'unit_price': result['unitPrice'].toString(),
        'currency': result['currency'],
        'notes': result['notes'],
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم إضافة السطر بنجاح'),
            backgroundColor: AppColors.success,
          ),
        );
        _loadInvoice();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    }
  }

  Future<void> _editLine(InvoiceLineModel line) async {
    final result = await _showLineDialog(line: line);
    if (result == null) return;
    try {
      await _api.patch('invoices/${widget.invoiceId}/lines/${line.lineId}', data: {
        'product_code': result['productCode'],
        'product_name': result['productName'],
        'quantity': result['quantity'].toString(),
        'unit_price': result['unitPrice'].toString(),
        'currency': result['currency'],
        'notes': result['notes'],
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم تحديث السطر بنجاح'),
            backgroundColor: AppColors.success,
          ),
        );
        _loadInvoice();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    }
  }

  Future<void> _removeLine(InvoiceLineModel line) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف السطر'),
        content: Text('هل تريد حذف السطر "${line.productName.isEmpty ? line.productCode : line.productName}"؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('إلغاء'),
          ),
          AppButton(
            onPressed: () => Navigator.pop(ctx, true),
            label: 'حذف',
            variant: AppButtonVariant.danger,
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _api.delete('invoices/${widget.invoiceId}/lines/${line.lineId}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم حذف السطر بنجاح'),
            backgroundColor: AppColors.warning,
          ),
        );
        _loadInvoice();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    }
  }

  Future<Map<String, dynamic>?> _showLineDialog({InvoiceLineModel? line}) async {
    final currency = _invoice?.currency ?? CurrencyHelper.baseCurrency;
    final quantityController =
        TextEditingController(text: line != null ? line.quantity.toString() : '1');
    final priceController =
        TextEditingController(text: line != null ? line.unitPrice.toString() : '');
    final notesController =
        TextEditingController(text: line?.notes ?? '');
    Product? selectedProduct;
    String productCode = line?.productCode ?? '';
    String productName = line?.productName ?? '';
    final List<Product> products = [];
    String? productsError;
    bool productsLoaded = false;

    if (line == null) {
      try {
        products.addAll(await ProductRepository.getProducts());
        productsLoaded = true;
        if (products.isNotEmpty) {
          selectedProduct = null;
        }
      } catch (e) {
        productsError = ErrorUtils.sanitize(e);
      }
    }

    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          double calcTotal() {
            final qty = Decimal.tryParse(quantityController.text.trim()) ?? Decimal.zero;
            final price = Decimal.tryParse(priceController.text.trim()) ?? Decimal.zero;
            return (qty * price).toDouble();
          }

          return AlertDialog(
            title: Text(line == null ? 'إضافة سطر' : 'تعديل السطر'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (line == null)
                    DropdownButtonFormField<Product>(
                      key: const ValueKey('product-dropdown'),
                      initialValue: selectedProduct,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'المنتج',
                        border: OutlineInputBorder(),
                      ),
                      items: products
                          .map((p) => DropdownMenuItem(
                                value: p,
                                child: Text('${p.code} - ${p.name}'),
                              ))
                          .toList(),
                      onChanged: (p) {
                        setDialogState(() {
                          selectedProduct = p;
                          if (p != null) {
                            productCode = p.code;
                            productName = p.name;
                            if (priceController.text.trim().isEmpty) {
                              priceController.text = p.unitPrice.toString();
                            }
                          }
                        });
                      },
                    ),
                  if (line == null && !productsLoaded && productsError == null)
                    const Padding(
                      padding: EdgeInsets.all(8),
                      child: CircularProgressIndicator(),
                    ),
                  if (productsError != null)
                    Padding(
                      padding: const EdgeInsets.all(8),
                      child: Text(
                        productsError!,
                        style: const TextStyle(color: AppColors.danger),
                      ),
                    ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: quantityController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'الكمية',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: priceController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'سعر الوحدة',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: notesController,
                    decoration: const InputDecoration(
                      labelText: 'ملاحظات',
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 2,
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      const Text('الإجمالي: '),
                      Text(
                        formatMoneyCurrency(
                          parseMoney(calcTotal().toString()) ?? Decimal.zero,
                          currency: currency,
                        ),
                        style: AppTextStyles.moneyMedium,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('إلغاء'),
              ),
              ElevatedButton(
                onPressed: () {
                  final qty = Decimal.tryParse(quantityController.text.trim());
                  final priceStr = priceController.text.trim();
                  if ((line == null && selectedProduct == null)) {
                    ScaffoldMessenger.of(ctx).showSnackBar(
                      const SnackBar(content: Text('اختر منتجاً'), backgroundColor: AppColors.danger),
                    );
                    return;
                  }
                  if (qty == null || qty <= Decimal.zero) {
                    ScaffoldMessenger.of(ctx).showSnackBar(
                      const SnackBar(content: Text('أدخل كمية صحيحة'), backgroundColor: AppColors.danger),
                    );
                    return;
                  }
                  final price = Decimal.tryParse(priceStr);
                  if (price == null || price < Decimal.zero) {
                    ScaffoldMessenger.of(ctx).showSnackBar(
                      const SnackBar(content: Text('أدخل سعراً صحيحاً'), backgroundColor: AppColors.danger),
                    );
                    return;
                  }
                  Navigator.pop(ctx, {
                    'productCode': productCode,
                    'productName': productName,
                    'quantity': qty,
                    'unitPrice': price,
                    'currency': currency,
                    'notes': notesController.text.trim(),
                  });
                },
                child: const Text('حفظ'),
              ),
            ],
          );
        },
      ),
    );
    return result;
  }

  Future<String?> _showReasonDialog(String title) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: 'السبب',
            border: OutlineInputBorder(),
          ),
          maxLines: 3,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('تأكيد'),
          ),
        ],
      ),
    );
    return result?.isEmpty == true ? null : result;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          _invoice != null
              ? 'فاتورة ${_invoice!.number ?? '#${widget.invoiceId.substring(0, 8)}'}'
              : 'تفاصيل الفاتورة',
        ),
        centerTitle: true,
        actions: [
          if (_invoice != null && _invoice!.isDraft) ...[
            IconButton(
              icon: const Icon(Icons.send, color: AppColors.success),
              onPressed: _postInvoice,
              tooltip: 'ترحيل',
            ),
          ],
          if (_invoice != null && _invoice!.isPosted) ...[
            IconButton(
              icon: const Icon(Icons.cancel, color: AppColors.warning),
              onPressed: _cancelInvoice,
              tooltip: 'إلغاء',
            ),
            IconButton(
              icon: const Icon(Icons.reply, color: AppColors.secondary),
              onPressed: _returnInvoice,
              tooltip: 'مرتجع',
            ),
          ],
        ],
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadInvoice, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const LoadingState(skeleton: false);
    if (_invoice == null) return const EmptyState(
      icon: Icons.receipt_long,
      title: 'الفاتورة غير موجودة',
      message: 'لم يتم العثور على الفاتورة المطلوبة',
    );

    final inv = _invoice!;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppDimens.s3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    StatusChip(status: inv.status),
                    const Spacer(),
                    if (inv.number != null)
                      Text(
                        '#${inv.number}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                _infoRow('التاريخ', DateFormat('yyyy-MM-dd').format(inv.date)),
                _infoRow('العميل', inv.customerName),
                _infoRow('العملة', inv.currency),
                if (inv.paymentType.isNotEmpty)
                  _infoRow('نوع الدفع', inv.paymentType),
                if (inv.siteName != null && inv.siteName!.isNotEmpty)
                  _infoRow('الموقع', inv.siteName!),
                if (inv.journalEntryId != null && inv.journalEntryId!.isNotEmpty)
                  _journalEntryLink(inv.journalEntryId!),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Text(
                  'بنود الفاتورة',
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              if (inv.isDraft)
                AppButton(
                  onPressed: _addLine,
                  icon: Icons.add,
                  label: 'إضافة بند',
                  variant: AppButtonVariant.secondary,
                ),
            ],
          ),
          const SizedBox(height: 8),
          AppCard(
            padding: EdgeInsets.zero,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingRowHeight: AppDimens.rowHeight,
                dataRowMaxHeight: AppDimens.rowHeight,
                dataRowMinHeight: AppDimens.rowHeight,
                columns: [
                  ...const [
                    DataColumn(label: Text('المنتج')),
                    DataColumn(label: Text('الكمية'), numeric: true),
                    DataColumn(label: Text('سعر الوحدة'), numeric: true),
                    DataColumn(label: Text('المبلغ'), numeric: true),
                    DataColumn(label: Text('الضريبة'), numeric: true),
                  ],
                  if (inv.isDraft) const DataColumn(label: Text('إجراءات')),
                ],
                rows: inv.lines.map((line) {
                  return DataRow(cells: [
                    DataCell(Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          line.productCode,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                        if (line.productName.isNotEmpty)
                          Text(
                            line.productName,
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.textSecondary,
                            ),
                          ),
                      ],
                    )),
                    DataCell(Text(formatMoney(line.quantity))),
                    DataCell(Text(formatMoney(line.unitPrice, decimals: currencyDecimals(_invoice?.currency)))),
                    DataCell(Text(
                      formatMoneyCurrency(line.total, currency: _invoice?.currency),
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    )),
                    DataCell(Text(
                      line.taxAmount != null
                          ? formatMoneyCurrency(line.taxAmount!, currency: _invoice?.currency)
                          : '-',
                    )),
                    if (inv.isDraft)
                      DataCell(Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.edit, size: 18, color: AppColors.edit),
                            tooltip: 'تعديل',
                            onPressed: () => _editLine(line),
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete, size: 18, color: AppColors.danger),
                            tooltip: 'حذف',
                            onPressed: () => _removeLine(line),
                          ),
                        ],
                      )),
                  ]);
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 12),
          AppCard(
            child: Column(
              children: [
                _totalsRow('المجموع الفرعي', formatMoneyCurrency(inv.subtotal, currency: _invoice?.currency)),
                const Divider(),
                _totalsRow('الضريبة', formatMoneyCurrency(inv.taxAmount, currency: _invoice?.currency)),
                const Divider(),
                _totalsRow(
                  'الإجمالي',
                  formatMoneyCurrency(inv.total, currency: _invoice?.currency),
                  isBold: true,
                ),
                if (inv.totalWithTax != null) ...[
                  const Divider(),
                  _totalsRow(
                    'الإجمالي شامل الضريبة',
                    formatMoneyCurrency(inv.totalWithTax!, currency: _invoice?.currency),
                    isBold: true,
                  ),
                ],
              ],
            ),
          ),
          if (inv.notes != null && inv.notes!.isNotEmpty) ...[
            const SizedBox(height: 16),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'ملاحظات',
                    style: AppTextStyles.titleSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(inv.notes!),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppDimens.s1),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  void _openJournalEntry(String entryId) {
    context.go('/journal-entries/$entryId');
  }

  Widget _journalEntryLink(String entryId) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppDimens.s1),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const SizedBox(
            width: 100,
            child: Text(
              'القيد المحاسبي:',
              style: TextStyle(
                color: AppColors.textSecondary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: ActionChip(
              avatar: const Icon(Icons.receipt_long, size: 18),
              label: Text(
                '#${entryId.substring(0, entryId.length > 8 ? 8 : entryId.length)}',
                style: const TextStyle(fontWeight: FontWeight.w500),
              ),
              onPressed: () => _openJournalEntry(entryId),
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              tooltip: 'عرض القيد',
            ),
          ),
          IconButton(
            icon: const Icon(Icons.open_in_new, size: 20),
            tooltip: 'عرض القيد',
            onPressed: () => _openJournalEntry(entryId),
          ),
        ],
      ),
    );
  }

  Widget _totalsRow(String label, String value, {bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppDimens.s1),
      child: Row(
        children: [
          Text(
            label,
            style: isBold ? AppTextStyles.titleMedium : AppTextStyles.bodyMedium,
          ),
          const Spacer(),
          Text(
            value,
            style: isBold
                ? AppTextStyles.moneyLarge
                : AppTextStyles.moneyMedium,
          ),
        ],
      ),
    );
  }
}
