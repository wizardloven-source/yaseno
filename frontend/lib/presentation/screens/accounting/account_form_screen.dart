import 'package:flutter/material.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/error_logger.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/app_widgets.dart';

class AccountFormScreen extends StatefulWidget {
  final String? accountCode;
  final String? parentCode;

  const AccountFormScreen({super.key, this.accountCode, this.parentCode});

  bool get isEditMode => accountCode != null;

  @override
  State<AccountFormScreen> createState() => _AccountFormScreenState();
}

class _AccountFormScreenState extends State<AccountFormScreen> {
  final ApiService _api = ApiService();
  final _formKey = GlobalKey<FormState>();
  final _codeController = TextEditingController();
  final _nameController = TextEditingController();
  final _notesController = TextEditingController();
  final _openingBalanceController = TextEditingController();
  String _accountType = 'asset';
  String? _parentCode;
  String _currency = 'USD';
  bool _isLoading = false;
  bool _isInitialLoading = false;
  List<Map<String, dynamic>> _accounts = [];
  List<Map<String, dynamic>> _currencies = [];

  @override
  void initState() {
    super.initState();
    _loadDropdownData();
    if (widget.isEditMode) _loadAccount();
  }

  Future<void> _loadDropdownData() async {
    setState(() => _isInitialLoading = true);
    try {
      final accounts = await _api.get('accounts');
      final currencies = await _api.get('currency');
      final accData = accounts['data'] ?? accounts;
      final curData = currencies['data'] ?? currencies;
      setState(() {
        _accounts = ((accData is Map ? accData['accounts'] ?? accData['items'] : accData) ?? []).cast<Map<String, dynamic>>();
        _currencies = ((curData is Map ? curData['items'] : curData) ?? []).cast<Map<String, dynamic>>();
        if (!widget.isEditMode &&
            widget.parentCode != null &&
            _accounts.any((a) => a['code'] == widget.parentCode)) {
          _parentCode = widget.parentCode;
        }
        _isInitialLoading = false;
      });
    } catch (e, s) {
      await ErrorLogger.log('acct_form_dropdown', e, s);
      if (mounted) setState(() => _isInitialLoading = false);
    }
  }

  Future<void> _loadAccount() async {
    try {
      final response = await _api.get('accounts');
      final data = response['data'] ?? response;
      final items = ((data is Map ? data['accounts'] ?? data['items'] : data) ?? []).cast<Map<String, dynamic>>();
      final existing = items.firstWhere(
        (a) => a['code'] == widget.accountCode,
        orElse: () => <String, dynamic>{},
      );
      if (existing.isNotEmpty) {
        _codeController.text = existing['code'] ?? '';
        _nameController.text = existing['name'] ?? '';
        _notesController.text = existing['description'] ?? '';
        setState(() {
          _accountType = existing['account_type'] ?? 'asset';
          _parentCode = existing['parent_code'];
          _currency = existing['currency'] ?? 'USD';
        });
      }
    } catch (e, s) {
      await ErrorLogger.log('acct_form_load_account', e, s);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);
    try {
      final openingBalance =
          double.tryParse(_openingBalanceController.text.trim());
      final payload = {
        'code': _codeController.text.trim(),
        'name': _nameController.text.trim(),
        'account_type': _accountType,
        'parent_code': _parentCode,
        'currency': _currency,
        'description': _notesController.text.trim().isNotEmpty ? _notesController.text.trim() : null,
        if (!widget.isEditMode && openingBalance != null)
          'opening_balance': openingBalance,
      };
      if (widget.isEditMode) {
        await _api.put('accounts/${widget.accountCode}', data: payload);
      } else {
        await _api.post('accounts', data: payload);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.isEditMode ? 'تم تعديل الحساب بنجاح' : 'تم إضافة الحساب بنجاح'),
            backgroundColor: AppColors.success,
          ),
        );
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _codeController.dispose();
    _nameController.dispose();
    _notesController.dispose();
    _openingBalanceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEditMode ? 'تعديل حساب' : 'إضافة حساب'),
        centerTitle: true,
      ),
      body: _isInitialLoading
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: ListView(
                  children: [
                    TextFormField(
                      controller: _codeController,
                      decoration: const InputDecoration(
                        labelText: 'رمز الحساب',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.code),
                      ),
                      enabled: !widget.isEditMode,
                      validator: (v) => (v == null || v.trim().isEmpty)
                          ? 'مطلوب'
                          : !RegExp(r'^\d+$').hasMatch(v.trim())
                              ? 'يجب أن يتكون الرمز من أرقام فقط'
                              : v.trim().length < 3
                                  ? 'يجب أن يكون الرمز 3 أرقام على الأقل'
                                  : v.trim().length > 20
                                      ? 'يجب ألا يتجاوز الرمز 20 رقماً'
                                      : null,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: 'اسم الحساب',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.badge),
                      ),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'مطلوب' : null,
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _accountType,
                      decoration: const InputDecoration(
                        labelText: 'نوع الحساب',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.category),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'asset', child: Text('أصول')),
                        DropdownMenuItem(value: 'liability', child: Text('خصوم')),
                        DropdownMenuItem(value: 'equity', child: Text('حقوق ملكية')),
                        DropdownMenuItem(value: 'revenue', child: Text('إيرادات')),
                        DropdownMenuItem(value: 'expense', child: Text('مصروفات')),
                      ],
                      onChanged: (v) => setState(() => _accountType = v!),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _parentCode,
                      decoration: const InputDecoration(
                        labelText: 'الحساب الأب (اختياري)',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.account_tree),
                      ),
                      items: [
                        const DropdownMenuItem(value: null, child: Text('بدون حساب أب')),
                        ..._accounts.where((a) => a['code'] != widget.accountCode).map(
                              (a) => DropdownMenuItem(
                                value: a['code'],
                                child: Text('${a['code']} - ${a['name']}'),
                              ),
                            ),
                      ],
                      onChanged: (v) => setState(() => _parentCode = v),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: _currency,
                      decoration: const InputDecoration(
                        labelText: 'العملة',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.monetization_on),
                      ),
                      items: _currencies.isEmpty
                          ? const [
                              DropdownMenuItem(value: 'USD', child: Text('USD')),
                              DropdownMenuItem(value: 'SYP', child: Text('SYP')),
                            ]
                          : _currencies
                              .map((c) => DropdownMenuItem<String>(
                                    value: (c['code'] ?? c['currency_code'] ?? '').toString(),
                                    child: Text('${c['code'] ?? c['currency_code']} - ${c['name'] ?? ''}'),
                                  ))
                              .toList(),
                      onChanged: (v) => setState(() => _currency = v!),
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _openingBalanceController,
                      decoration: const InputDecoration(
                        labelText: 'الرصيد الافتتاحي',
                        hintText: '0.00',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.trending_up),
                        helperText: 'سيُستخدم في أرصدة الافتتاح (للحسابات الجديدة)',
                      ),
                      enabled: !widget.isEditMode,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _notesController,
                      decoration: const InputDecoration(
                        labelText: 'ملاحظات',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.notes),
                      ),
                      maxLines: 3,
                    ),
                    const SizedBox(height: AppDimens.s4),
                    AppButton(
                      expanded: true,
                      variant: AppButtonVariant.success,
                      icon: Icons.save,
                      label: widget.isEditMode ? 'تعديل' : 'حفظ',
                      loading: _isLoading,
                      onPressed: _save,
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
