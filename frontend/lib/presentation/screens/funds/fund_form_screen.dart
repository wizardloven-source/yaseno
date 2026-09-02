import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../widgets/app_widgets.dart';

class FundFormScreen extends StatefulWidget {
  final String? fundId;

  const FundFormScreen({super.key, this.fundId});

  @override
  State<FundFormScreen> createState() => _FundFormScreenState();
}

class _FundFormScreenState extends State<FundFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _codeController = TextEditingController();
  final _nameController = TextEditingController();
  final _accountCodeController = TextEditingController();
  final _openingBalanceController = TextEditingController(text: '0');
  String _fundType = 'main';
  String _currency = 'USD';
  bool _isSaving = false;
  bool _isLoadingEdit = false;
  List<Map<String, dynamic>> _currencies = [];

  bool get _isEdit => widget.fundId != null;

  @override
  void initState() {
    super.initState();
    _loadCurrencies();
    if (_isEdit) _loadFund();
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

  Future<void> _loadFund() async {
    setState(() => _isLoadingEdit = true);
    try {
      final response = await ApiService().getFund(widget.fundId!);
      final data = response['data'] ?? response;
      _codeController.text = '${data['code'] ?? ''}';
      _nameController.text = '${data['name'] ?? ''}';
      _accountCodeController.text = '${data['account_code'] ?? ''}';
      _fundType = data['fund_type'] ?? 'main';
      _currency = data['currency'] ?? 'USD';
      if (_currencies.isNotEmpty && !_currencies.any((c) => c['code'] == _currency)) {
        _currency = _currencies.first['code'] ?? CurrencyHelper.baseCurrency;
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    } finally {
      if (mounted) setState(() => _isLoadingEdit = false);
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSaving = true);
    try {
      final api = ApiService();
      dynamic res;
      if (_isEdit) {
        res = await api.put('funds/${widget.fundId}', data: {
          'name': _nameController.text.trim(),
          'fund_type': _fundType,
          'currency': _currency,
        });
      } else {
        res = await api.createFund({
          'code': _codeController.text.trim(),
          'name': _nameController.text.trim(),
          'account_code': _accountCodeController.text.trim(),
          'fund_type': _fundType,
          'currency': _currency,
          'opening_balance': double.tryParse(_openingBalanceController.text) ?? 0,
        });
      }
      if (res is Map && res['success'] == false) {
        throw Exception(res['message'] ?? 'فشل حفظ الصندوق');
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  void dispose() {
    _codeController.dispose();
    _nameController.dispose();
    _accountCodeController.dispose();
    _openingBalanceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_isEdit ? 'تعديل الصندوق' : 'إنشاء صندوق جديد')),
      body: _isLoadingEdit
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: ListView(
                  children: [
                    if (!_isEdit) ...[
                      TextFormField(
                        controller: _codeController,
                        decoration: const InputDecoration(labelText: 'رمز الصندوق', border: OutlineInputBorder()),
                        validator: (v) => (v == null || v.trim().isEmpty) ? 'مطلوب' : null,
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _accountCodeController,
                        decoration: const InputDecoration(labelText: 'رمز الحساب المرتبط', border: OutlineInputBorder()),
                        validator: (v) => (v == null || v.trim().isEmpty) ? 'مطلوب' : null,
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _openingBalanceController,
                        decoration: const InputDecoration(labelText: 'الرصيد الافتتاحي', border: OutlineInputBorder()),
                        keyboardType: TextInputType.number,
                      ),
                      const SizedBox(height: 16),
                    ],
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(labelText: 'اسم الصندوق', border: OutlineInputBorder()),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'مطلوب' : null,
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _fundType,
                      decoration: const InputDecoration(labelText: 'نوع الصندوق', border: OutlineInputBorder()),
                      items: const [
                        DropdownMenuItem(value: 'main', child: Text('رئيسي')),
                        DropdownMenuItem(value: 'sub', child: Text('فرعي')),
                        DropdownMenuItem(value: 'project', child: Text('مشروع')),
                      ],
                      onChanged: (v) => setState(() => _fundType = v!),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _currency,
                      decoration: const InputDecoration(labelText: 'العملة', border: OutlineInputBorder()),
                      items: _currencies.map((c) => DropdownMenuItem<String>(
                        value: (c['code'] ?? '').toString(),
                        child: Text('${c['code'] ?? ''} ${c['symbol'] != null ? "- ${c['symbol']}" : ''}'),
                      )).toList(),
                      onChanged: (v) => setState(() => _currency = v!),
                    ),
                    const SizedBox(height: 24),
                    AppButton(
                      label: _isEdit ? 'تحديث' : 'حفظ',
                      icon: Icons.save,
                      variant: _isEdit ? AppButtonVariant.edit : AppButtonVariant.success,
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
