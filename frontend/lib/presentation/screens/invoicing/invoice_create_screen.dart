import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../widgets/app_widgets.dart';

class _InvoiceLine {
  final productCodeController = TextEditingController();
  final productNameController = TextEditingController();
  final quantityController = TextEditingController(text: '1');
  final unitPriceController = TextEditingController();
  final notesController = TextEditingController();

  List<Map<String, dynamic>> productSuggestions = [];
  bool showProductSuggestions = false;
  bool isSearchingProducts = false;

  String get productCode => productCodeController.text.trim();
  String get productName => productNameController.text.trim();
  Decimal get quantity => parseMoney(quantityController.text) ?? Decimal.zero;
  Decimal get unitPrice => parseMoney(unitPriceController.text) ?? Decimal.zero;
  Decimal get total => quantity * unitPrice;

  void dispose() {
    productCodeController.dispose();
    productNameController.dispose();
    quantityController.dispose();
    unitPriceController.dispose();
    notesController.dispose();
  }
}

class InvoiceCreateScreen extends StatefulWidget {
  const InvoiceCreateScreen({super.key});

  @override
  State<InvoiceCreateScreen> createState() => _InvoiceCreateScreenState();
}

class _InvoiceCreateScreenState extends State<InvoiceCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final ApiService _api = ApiService();
  final _customerController = TextEditingController();
  final _notesController = TextEditingController();
  final _scrollController = ScrollController();

  bool _isSaving = false;
  DateTime _date = DateTime.now();
  String _currency = 'USD';
  String _paymentType = 'cash';
  double _taxRate = 0;

  String? _selectedCustomerId;
  List<Map<String, dynamic>> _allCustomers = [];
  List<Map<String, dynamic>> _customerSuggestions = [];
  bool _showCustomerSuggestions = false;
  bool _isSearchingCustomers = false;
  bool _showCustomerDropdown = false;

  List<Map<String, dynamic>> _customerBranches = [];
  String? _selectedBranchId;
  bool _showBranchSelector = false;

  List<Map<String, dynamic>> _currencies = [];
  List<_InvoiceLine> _lines = [_InvoiceLine()];

  @override
  void initState() {
    super.initState();
    _loadSettings();
    _loadCurrencies();
    _loadAllCustomers();
  }

  @override
  void dispose() {
    _customerController.dispose();
    _notesController.dispose();
    _scrollController.dispose();
    for (final line in _lines) {
      line.dispose();
    }
    super.dispose();
  }

  Future<void> _loadSettings() async {
    try {
      final response = await _api.getSettings();
      final data = response['data'] ?? response;
      if (data is Map && data.containsKey('tax_rate')) {
        setState(() => _taxRate = (data['tax_rate'] ?? 0).toDouble());
      }
    } catch (_) {}
  }

  Future<void> _loadCurrencies() async {
    try {
      final response = await _api.get('currency');
      final items = response['items'] ?? [];
      if (items is List && mounted) {
        setState(() => _currencies = items.cast<Map<String, dynamic>>());
      }
    } catch (_) {}
  }

  Future<void> _loadAllCustomers() async {
    try {
      final response = await _api.get('customers', queryParameters: {'limit': 500});
      final items = response['items'] ?? [];
      if (items is List && mounted) {
        setState(() => _allCustomers = items.cast<Map<String, dynamic>>());
      }
    } catch (_) {}
  }

  Future<void> _searchCustomers(String query) async {
    setState(() {
      _showCustomerDropdown = false;
    });
    if (query.length < 2) {
      setState(() {
        _customerSuggestions = _allCustomers.take(20).toList();
        _showCustomerSuggestions = query.isNotEmpty;
      });
      return;
    }
    final q = query.toLowerCase();
    final filtered = _allCustomers.where((c) {
      final name = (c['name'] ?? '').toString().toLowerCase();
      final code = (c['code'] ?? '').toString().toLowerCase();
      final phone = (c['phone'] ?? '').toString().toLowerCase();
      return name.contains(q) || code.contains(q) || phone.contains(q);
    }).toList();
    setState(() {
      _customerSuggestions = filtered;
      _showCustomerSuggestions = true;
    });
  }

  void _showAllCustomers() async {
    if (_allCustomers.isEmpty) {
      await _loadAllCustomers();
    }
    setState(() {
      _customerSuggestions = _allCustomers;
      _showCustomerSuggestions = true;
      _showCustomerDropdown = true;
    });
  }

  void _selectCustomer(Map<String, dynamic> customer) {
    final cid = (customer['id'] ?? customer['_id'])?.toString();
    setState(() {
      _customerController.text = customer['name'] ?? '';
      _selectedCustomerId = cid;
      _customerSuggestions = [];
      _showCustomerSuggestions = false;
      _showCustomerDropdown = false;
      _selectedBranchId = null;
      _customerBranches = [];
      _showBranchSelector = false;
    });
    if (cid != null) _loadBranches(cid);
  }

  Future<void> _loadBranches(String customerId) async {
    try {
      final response = await _api.get('customers/$customerId/branches');
      final items = response['items'] ?? [];
      if (items is List && mounted) {
        setState(() {
          _customerBranches = items.cast<Map<String, dynamic>>();
          _showBranchSelector = _customerBranches.isNotEmpty;
        });
      }
    } catch (_) {}
  }

  Future<void> _searchProducts(int lineIndex, String query) async {
    final line = _lines[lineIndex];
    setState(() {
      line.showProductSuggestions = false;
    });
    if (query.length < 2) {
      setState(() {
        line.productSuggestions = [];
        line.showProductSuggestions = query.isNotEmpty;
      });
      return;
    }
    setState(() => line.isSearchingProducts = true);
    try {
      final response = await _api.get('products', queryParameters: {'q': query});
      final items = response['items'] ?? [];
      if (items is List && mounted) {
        setState(() {
          line.productSuggestions = items.cast<Map<String, dynamic>>();
          line.showProductSuggestions = true;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          line.productSuggestions = [];
          line.showProductSuggestions = false;
        });
      }
    } finally {
      if (mounted) setState(() => line.isSearchingProducts = false);
    }
  }

  void _showAllProducts(int lineIndex) async {
    final line = _lines[lineIndex];
    try {
      final response = await _api.get('products', queryParameters: {'limit': 500});
      final items = response['items'] ?? [];
      if (items is List && mounted) {
        setState(() {
          line.productSuggestions = items.cast<Map<String, dynamic>>();
          line.showProductSuggestions = true;
        });
      }
    } catch (_) {}
  }

  void _selectProduct(int lineIndex, Map<String, dynamic> product) {
    final line = _lines[lineIndex];
    setState(() {
      line.productCodeController.text = product['code'] ?? product['sku'] ?? '';
      line.productNameController.text = product['name'] ?? '';
      line.unitPriceController.text =
          formatMoney(product['unit_price'] ?? product['price'] ?? 0);
      line.productSuggestions = [];
      line.showProductSuggestions = false;
    });
  }

  void _addLine() {
    setState(() => _lines.add(_InvoiceLine()));
  }

  void _removeLine(int index) {
    if (_lines.length <= 1) return;
    setState(() {
      _lines[index].dispose();
      _lines.removeAt(index);
    });
  }

  Decimal get _subtotal =>
      _lines.fold(Decimal.zero, (sum, line) => sum + line.total);
  Decimal get _tax =>
      (_subtotal * parseMoneyOrZero(_taxRate) / Decimal.fromInt(100))
          .toDecimal();
  Decimal get _total => _subtotal + _tax;

  Future<void> _selectDate(BuildContext context) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2000),
      lastDate: DateTime(2101),
    );
    if (picked != null && picked != _date) {
      setState(() => _date = picked);
    }
  }

  Future<void> _createInvoice() async {
    if (!_formKey.currentState!.validate()) return;
    if (_customerController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('الرجاء اختيار العميل')),
      );
      return;
    }
    final validLines = _lines.where((l) => l.productName.isNotEmpty).toList();
    if (validLines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('الرجاء إضافة بند واحد على الأقل')),
      );
      return;
    }

    setState(() => _isSaving = true);
    try {
      await _api.post('invoices', data: {
        'customer_id': _selectedCustomerId ?? '',
        'customer_name': _customerController.text.trim(),
        if (_selectedBranchId != null) 'site_id': _selectedBranchId,
        'currency': _currency,
        'payment_type': _paymentType,
        'date': _date.toIso8601String().split('T')[0],
        'lines': validLines.map((l) => {
          'product_code': l.productCode,
          'product_name': l.productName,
          'quantity': l.quantity.toDouble(),
          'unit_price': l.unitPrice.toDouble(),
          'currency': _currency,
          if (l.notesController.text.trim().isNotEmpty)
            'notes': l.notesController.text.trim(),
        }).toList(),
        if (_notesController.text.trim().isNotEmpty)
          'notes': _notesController.text.trim(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم إنشاء الفاتورة بنجاح'),
            backgroundColor: AppColors.success,
          ),
        );
        context.go('/invoices');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      appBar: AppBar(title: const Text('إنشاء فاتورة جديدة')),
      body: GestureDetector(
        onTap: () {
          setState(() {
            _showCustomerSuggestions = false;
            _showCustomerDropdown = false;
          });
          for (final line in _lines) {
            line.showProductSuggestions = false;
          }
        },
        child: Form(
          key: _formKey,
          child: ListView(
            controller: _scrollController,
            padding: const EdgeInsets.all(16),
            children: [
              _buildCustomerField(isDark),
              if (_showBranchSelector && _customerBranches.isNotEmpty) ...[
                const SizedBox(height: 8),
                _buildBranchDropdown(isDark),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: _buildPaymentTypeDropdown(isDark)),
                  const SizedBox(width: 8),
                  Expanded(child: _buildCurrencyDropdown(isDark)),
                ],
              ),
              const SizedBox(height: 12),
              _buildDateField(isDark),
              const SizedBox(height: 20),
              Text('بنود الفاتورة', style: AppTextStyles.titleMedium),
              const SizedBox(height: 8),
              _buildItemsTable(isDark),
              const SizedBox(height: 8),
              _buildAddLineButton(),
              const SizedBox(height: 20),
              _buildTotalsSection(),
              const SizedBox(height: 12),
              _buildNotesField(),
              const SizedBox(height: 20),
              _buildSaveButton(),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCustomerField(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _customerController,
          decoration: InputDecoration(
            labelText: 'اسم العميل',
            prefixIcon: const Icon(Icons.person),
            border: const OutlineInputBorder(),
            suffixIcon: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_isSearchingCustomers)
                  const Padding(
                    padding: EdgeInsets.all(12),
                    child: SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)),
                  ),
                if (_customerController.text.isNotEmpty)
                  IconButton(
                    icon: const Icon(Icons.clear, size: 20),
                    onPressed: () {
                      setState(() {
                        _customerController.clear();
                        _selectedCustomerId = null;
                        _customerSuggestions = [];
                        _showCustomerSuggestions = false;
                        _showBranchSelector = false;
                        _customerBranches = [];
                      });
                    },
                  ),
                IconButton(
                  icon: const Icon(Icons.arrow_drop_down, size: 24),
                  onPressed: _showAllCustomers,
                  tooltip: 'اختر من القائمة',
                ),
              ],
            ),
          ),
          onChanged: _searchCustomers,
        ),
        if (_showCustomerSuggestions && _customerSuggestions.isNotEmpty)
          Container(
            constraints: const BoxConstraints(maxHeight: 220),
            decoration: BoxDecoration(
              border: Border.all(color: Theme.of(context).colorScheme.outline),
              borderRadius: BorderRadius.circular(AppDimens.radiusInput),
              color: Theme.of(context).colorScheme.surface,
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 8, offset: const Offset(0, 2))],
            ),
            child: ListView.builder(
              shrinkWrap: true,
              padding: EdgeInsets.zero,
              itemCount: _customerSuggestions.length,
              itemBuilder: (context, index) {
                final c = _customerSuggestions[index];
                final isSelected = c['id']?.toString() == _selectedCustomerId;
                return ListTile(
                  dense: true,
                  leading: Icon(Icons.person, size: 20, color: isSelected ? AppColors.primary : null),
                  title: Text(c['name'] ?? '', style: TextStyle(fontSize: 13, fontWeight: isSelected ? FontWeight.bold : FontWeight.normal, color: Theme.of(context).colorScheme.onSurface)),
                  subtitle: Text('${c['code'] ?? ''} ${c['phone'] != null ? "- ${c['phone']}" : ''}', style: TextStyle(fontSize: 11, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                  trailing: isSelected ? Icon(Icons.check, size: 18, color: AppColors.primary) : null,
                  onTap: () => _selectCustomer(c),
                );
              },
            ),
          ),
      ],
    );
  }

  Widget _buildBranchDropdown(bool isDark) {
    return DropdownButtonFormField<String>(
      value: _selectedBranchId,
      decoration: const InputDecoration(
        labelText: 'الفرع',
        prefixIcon: Icon(Icons.account_balance, size: 20),
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: _customerBranches.map((b) {
        return DropdownMenuItem<String>(
          value: b['id']?.toString(),
          child: Text(b['name'] ?? b['code'] ?? '', style: const TextStyle(fontSize: 13)),
        );
      }).toList(),
      onChanged: (v) => setState(() => _selectedBranchId = v),
    );
  }

  Widget _buildPaymentTypeDropdown(bool isDark) {
    return DropdownButtonFormField<String>(
      value: _paymentType,
      decoration: const InputDecoration(
        labelText: 'نوع الدفع',
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: const [
        DropdownMenuItem(value: 'cash', child: Text('نقدي')),
        DropdownMenuItem(value: 'credit', child: Text('آجل')),
        DropdownMenuItem(value: 'bank_transfer', child: Text('تحويل بنكي')),
      ],
      onChanged: (v) => setState(() => _paymentType = v!),
    );
  }

  Widget _buildCurrencyDropdown(bool isDark) {
    final items = _currencies.map((c) {
      final code = c['code'] ?? '';
      final symbol = c['symbol'] ?? '';
      return DropdownMenuItem<String>(
        value: code,
        child: Text('$code ${symbol.isNotEmpty ? "($symbol)" : ""}', style: const TextStyle(fontSize: 13)),
      );
    }).toList();
    if (items.isEmpty) {
      items.add(const DropdownMenuItem(value: 'USD', child: Text('USD')));
    }
    final validCurrency = _currencies.any((c) => c['code'] == _currency) ? _currency : 'USD';
    return DropdownButtonFormField<String>(
      value: validCurrency,
      decoration: const InputDecoration(
        labelText: 'العملة',
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: items,
      onChanged: (v) => setState(() => _currency = v!),
    );
  }

  Widget _buildDateField(bool isDark) {
    return InkWell(
      onTap: () => _selectDate(context),
      child: InputDecorator(
        decoration: const InputDecoration(
          labelText: 'التاريخ',
          prefixIcon: Icon(Icons.calendar_today),
          border: OutlineInputBorder(),
          isDense: true,
        ),
        child: Text(
          '${_date.year}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')}',
          style: const TextStyle(fontSize: 14),
        ),
      ),
    );
  }

  Widget _buildItemsTable(bool isDark) {
    final headerBg = isDark ? const Color(0xFF1A2744) : AppColors.primaryContainer;
    final headerFg = isDark ? Colors.white : AppColors.primary;
    final borderColor = Theme.of(context).colorScheme.outline.withOpacity(0.3);
    final isWide = MediaQuery.of(context).size.width > 700;

    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          Container(
            color: headerBg,
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 10),
            child: Row(
              children: [
                const SizedBox(width: 28, child: Text('#', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold))),
                Expanded(flex: 3, child: Text('الكود', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: headerFg))),
                Expanded(flex: 4, child: Text('المنتج', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: headerFg))),
                if (isWide)
                  Expanded(flex: 2, child: Text('ملاحظات', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: headerFg))),
                Expanded(flex: 2, child: Text('الكمية', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: headerFg), textAlign: TextAlign.center)),
                Expanded(flex: 2, child: Text('السعر', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: headerFg), textAlign: TextAlign.center)),
                Expanded(flex: 2, child: Text('الإجمالي', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: headerFg), textAlign: TextAlign.center)),
                const SizedBox(width: 32),
              ],
            ),
          ),
          for (var i = 0; i < _lines.length; i++)
            _buildTableRow(i, _lines[i], isDark, isWide, borderColor),
          _buildEmptyRow(isDark, borderColor),
          _buildTableFooter(isDark),
        ],
      ),
    );
  }

  Widget _buildTableRow(int index, _InvoiceLine line, bool isDark, bool isWide, Color borderColor) {
    final onSurface = Theme.of(context).colorScheme.onSurface;
    final surfaceVariant = Theme.of(context).colorScheme.onSurfaceVariant;
    return Container(
      decoration: BoxDecoration(border: Border(bottom: BorderSide(color: borderColor))),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(width: 28, child: Text('${index + 1}', style: TextStyle(fontSize: 11, color: surfaceVariant))),
              Expanded(
                flex: 3,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: TextField(
                    controller: line.productCodeController,
                    decoration: const InputDecoration(
                      hintText: 'الكود', border: InputBorder.none, isDense: true,
                      contentPadding: EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                    ),
                    style: TextStyle(fontSize: 12, color: onSurface),
                  ),
                ),
              ),
              Expanded(
                flex: 4,
                child: _buildInlineProductField(index, line, onSurface, surfaceVariant),
              ),
              if (isWide)
                Expanded(
                  flex: 2,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 2),
                    child: TextField(
                      controller: line.notesController,
                      decoration: const InputDecoration(
                        hintText: 'ملاحظات', border: InputBorder.none, isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                      ),
                      style: TextStyle(fontSize: 11, color: surfaceVariant),
                    ),
                  ),
                ),
              Expanded(
                flex: 2,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: TextField(
                    controller: line.quantityController,
                    decoration: const InputDecoration(
                      hintText: '0', border: InputBorder.none, isDense: true,
                      contentPadding: EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                    ),
                    style: TextStyle(fontSize: 12, color: onSurface),
                    keyboardType: TextInputType.number,
                    textAlign: TextAlign.center,
                    onChanged: (_) => setState(() {}),
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: TextField(
                    controller: line.unitPriceController,
                    decoration: const InputDecoration(
                      hintText: '0', border: InputBorder.none, isDense: true,
                      contentPadding: EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                    ),
                    style: TextStyle(fontSize: 12, color: onSurface),
                    keyboardType: TextInputType.number,
                    textAlign: TextAlign.center,
                    onChanged: (_) => setState(() {}),
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: Text(formatMoney(line.total), style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: onSurface), textAlign: TextAlign.center),
                ),
              ),
              SizedBox(
                width: 32,
                child: _lines.length > 1
                    ? IconButton(
                        icon: Icon(Icons.close, size: 15, color: AppColors.danger),
                        onPressed: () => _removeLine(index),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                        tooltip: 'حذف',
                      )
                    : const SizedBox.shrink(),
              ),
            ],
          ),
          if (!isWide)
            Padding(
              padding: const EdgeInsets.only(left: 28, right: 32, bottom: 2),
              child: TextField(
                controller: line.notesController,
                decoration: const InputDecoration(
                  hintText: 'ملاحظات البند', border: InputBorder.none, isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                ),
                style: TextStyle(fontSize: 11, color: surfaceVariant),
              ),
            ),
          if (line.showProductSuggestions && line.productSuggestions.isNotEmpty)
            Container(
              constraints: const BoxConstraints(maxHeight: 150),
              decoration: BoxDecoration(
                border: Border.all(color: Theme.of(context).colorScheme.outline),
                borderRadius: BorderRadius.circular(6),
                color: Theme.of(context).colorScheme.surface,
                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 6, offset: const Offset(0, 2))],
              ),
              margin: const EdgeInsets.only(top: 2, bottom: 4),
              child: ListView.builder(
                shrinkWrap: true,
                padding: EdgeInsets.zero,
                itemCount: line.productSuggestions.length,
                itemBuilder: (ctx, i) {
                  final p = line.productSuggestions[i];
                  final price = p['unit_price'] ?? p['price'] ?? '';
                  return ListTile(
                    dense: true,
                    leading: const Icon(Icons.inventory_2, size: 16),
                    title: Text(p['name'] ?? '', style: TextStyle(fontSize: 12, color: onSurface)),
                    subtitle: Text('${p['code'] ?? ''}${price.toString().isNotEmpty ? ' - $price' : ''}', style: TextStyle(fontSize: 10, color: surfaceVariant)),
                    onTap: () => _selectProduct(index, p),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildInlineProductField(int index, _InvoiceLine line, Color onSurface, Color surfaceVariant) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: line.productNameController,
              decoration: InputDecoration(
                hintText: 'اسم المنتج',
                border: InputBorder.none,
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                suffixIcon: line.isSearchingProducts
                    ? const Padding(
                        padding: EdgeInsets.all(8),
                        child: SizedBox(height: 14, width: 14, child: CircularProgressIndicator(strokeWidth: 1.5)),
                      )
                    : null,
                suffixIconConstraints: const BoxConstraints(maxWidth: 20, maxHeight: 20),
              ),
              style: TextStyle(fontSize: 12, color: onSurface),
              onChanged: (value) => _searchProducts(index, value),
            ),
          ),
          GestureDetector(
            onTap: () => _showAllProducts(index),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Icon(Icons.arrow_drop_down, size: 20, color: surfaceVariant),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyRow(bool isDark, Color borderColor) {
    return GestureDetector(
      onTap: _addLine,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(border: Border(bottom: BorderSide(color: borderColor))),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.add_circle_outline, size: 16, color: AppColors.primary.withOpacity(0.6)),
            const SizedBox(width: 4),
            Text('اضغط لإضافة بند', style: TextStyle(fontSize: 11, color: AppColors.primary.withOpacity(0.6))),
          ],
        ),
      ),
    );
  }

  Widget _buildTableFooter(bool isDark) {
    final onSurface = Theme.of(context).colorScheme.onSurface;
    final surfaceVariant = Theme.of(context).colorScheme.onSurfaceVariant;
    return Container(
      color: isDark ? const Color(0xFF0D1117) : Colors.grey.shade50,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text('المجموع: ${formatMoney(_subtotal)}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: onSurface)),
                Text('الضريبة (${_taxRate.toStringAsFixed(0)}%): ${formatMoney(_tax)}', style: TextStyle(fontSize: 11, color: surfaceVariant)),
                Text('الإجمالي: ${formatMoney(_total)}', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.primary)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAddLineButton() {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: _addLine,
        icon: const Icon(Icons.add, size: 18),
        label: const Text('إضافة بند'),
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 10),
          side: BorderSide(color: AppColors.primary.withOpacity(0.5)),
        ),
      ),
    );
  }

  Widget _buildTotalsSection() {
    return AppCard(
      child: Column(
        children: [
          _buildTotalRow('المجموع الفرعي', _subtotal),
          const Divider(),
          _buildTotalRow('الضريبة (${_taxRate.toStringAsFixed(0)}%)', _tax),
          const Divider(thickness: 2),
          _buildTotalRow('الإجمالي', _total, isBold: true),
        ],
      ),
    );
  }

  Widget _buildTotalRow(String label, Decimal value, {bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppDimens.s1),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: isBold ? AppTextStyles.titleMedium : AppTextStyles.bodyLarge),
          Text(formatMoneyCurrency(value, currency: _currency), style: isBold ? AppTextStyles.moneyLarge : AppTextStyles.moneyMedium),
        ],
      ),
    );
  }

  Widget _buildNotesField() {
    return TextField(
      controller: _notesController,
      decoration: const InputDecoration(
        labelText: 'ملاحظات الفاتورة (اختياري)',
        prefixIcon: Icon(Icons.note),
        border: OutlineInputBorder(),
      ),
      maxLines: 2,
    );
  }

  Widget _buildSaveButton() {
    return AppButton(
      onPressed: _createInvoice,
      label: 'إنشاء الفاتورة',
      icon: Icons.add,
      variant: AppButtonVariant.success,
      loading: _isSaving,
      expanded: true,
    );
  }
}
