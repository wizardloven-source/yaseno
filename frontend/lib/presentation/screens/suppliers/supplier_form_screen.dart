import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../../data/models/supplier_model.dart';
import '../../../data/repositories/supplier_repository.dart';
import '../../widgets/loading_state.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../widgets/app_widgets.dart';
import '../../../utils/currency_helper.dart';

class SupplierFormScreen extends StatefulWidget {
  final Supplier? supplier;
  final String? supplierId;

  const SupplierFormScreen({super.key, this.supplier, this.supplierId});

  @override
  State<SupplierFormScreen> createState() => _SupplierFormScreenState();
}

class _SupplierFormScreenState extends State<SupplierFormScreen> {
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;
  bool _isEditing = false;

  // Controllers
  final _codeController = TextEditingController();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _mobileController = TextEditingController();
  final _streetController = TextEditingController();
  final _cityController = TextEditingController();
  final _taxNumberController = TextEditingController();
  final _creditLimitController = TextEditingController();
  final _notesController = TextEditingController();

  String _selectedCountry = 'LB';
  String _selectedCurrency = 'USD';
  String _selectedStatus = 'active';
  List<String> _currencies = [];

  final List<String> _countries = ['LB', 'US', 'UK', 'FR', 'AE', 'SA', 'CN', 'IN'];
  final List<String> _statuses = ['active', 'inactive', 'suspended', 'blocked'];

  @override
  void initState() {
    super.initState();
    _loadCurrencies();
    _isEditing = widget.supplier != null || (widget.supplierId != null && widget.supplierId!.isNotEmpty);
    if (widget.supplier != null) {
      _fillForm();
    } else if (_isEditing) {
      _loadRecord();
    }
  }

  Future<void> _loadCurrencies() async {
    await CurrencyHelper.load();
    if (mounted) {
      setState(() {
        _currencies = CurrencyHelper.currencyCodes;
        if (!_currencies.contains(_selectedCurrency)) {
          _selectedCurrency = CurrencyHelper.baseCurrency;
        }
      });
    }
  }

  Future<void> _loadRecord() async {
    setState(() => _isLoading = true);
    try {
      final supplier = await SupplierRepository.getSupplier(widget.supplierId!);
      if (supplier != null) {
        _fillFromSupplier(supplier);
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('المورد غير موجود'), backgroundColor: AppColors.danger),
          );
          Navigator.pop(context);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _fillFromSupplier(Supplier supplier) {
    _codeController.text = supplier.code;
    _nameController.text = supplier.name;
    _emailController.text = supplier.email ?? '';
    _phoneController.text = supplier.phone ?? '';
    _mobileController.text = supplier.mobile ?? '';
    _streetController.text = supplier.street ?? '';
    _cityController.text = supplier.city ?? '';
    _taxNumberController.text = supplier.taxNumber ?? '';
    _creditLimitController.text = formatMoney(supplier.creditLimit);
    _notesController.text = supplier.notes ?? '';
    _selectedCountry = supplier.country;
    _selectedCurrency = supplier.currency;
    _selectedStatus = supplier.status;
  }

  void _fillForm() {
    final supplier = widget.supplier!;
    _codeController.text = supplier.code;
    _nameController.text = supplier.name;
    _emailController.text = supplier.email ?? '';
    _phoneController.text = supplier.phone ?? '';
    _mobileController.text = supplier.mobile ?? '';
    _streetController.text = supplier.street ?? '';
    _cityController.text = supplier.city ?? '';
    _taxNumberController.text = supplier.taxNumber ?? '';
    _creditLimitController.text = formatMoney(supplier.creditLimit);
    _notesController.text = supplier.notes ?? '';
    _selectedCountry = supplier.country;
    _selectedCurrency = supplier.currency;
    _selectedStatus = supplier.status;
  }

  @override
  void dispose() {
    _codeController.dispose();
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _mobileController.dispose();
    _streetController.dispose();
    _cityController.dispose();
    _taxNumberController.dispose();
    _creditLimitController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _saveSupplier() async {
    if (!_formKey.currentState!.validate()) return;

    if (mounted) setState(() => _isLoading = true);

    try {
      final supplier = Supplier(
        id: widget.supplier?.id ?? '',
        code: _codeController.text,
        name: _nameController.text,
        email: _emailController.text.isNotEmpty ? _emailController.text : null,
        phone: _phoneController.text.isNotEmpty ? _phoneController.text : null,
        mobile: _mobileController.text.isNotEmpty ? _mobileController.text : null,
        street: _streetController.text.isNotEmpty ? _streetController.text : null,
        city: _cityController.text.isNotEmpty ? _cityController.text : null,
        country: _selectedCountry,
        taxNumber: _taxNumberController.text.isNotEmpty ? _taxNumberController.text : null,
        creditLimit: parseMoney(_creditLimitController.text) ?? Decimal.zero,
        currency: _selectedCurrency,
        notes: _notesController.text.isNotEmpty ? _notesController.text : null,
        status: _selectedStatus,
        createdAt: widget.supplier?.createdAt ?? DateTime.now(),
        updatedAt: DateTime.now(),
        version: widget.supplier?.version ?? 1,
      );

      Supplier? result;
      if (_isEditing) {
        result = await SupplierRepository.updateSupplier(supplier);
      } else {
        result = await SupplierRepository.createSupplier(supplier);
      }

      if (result != null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(_isEditing ? 'تم تحديث المورد بنجاح' : 'تم إنشاء المورد بنجاح'),
              backgroundColor: AppColors.success,
            ),
          );
          Navigator.pop(context, true);
        }
      } else {
        throw Exception('فشل في حفظ البيانات');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ErrorUtils.sanitize(e)),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: LoadingState(skeleton: false),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_isEditing ? 'تعديل مورد' : 'إضافة مورد جديد'),
        centerTitle: true,
        actions: [
          if (_isEditing)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () => _deleteSupplier(),
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // كود المورد
              TextFormField(
                controller: _codeController,
                decoration: const InputDecoration(
                  labelText: 'كود المورد *',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.code),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'يرجى إدخال كود المورد';
                  }
                  if (value.length < 2) {
                    return 'الكود يجب أن يكون على الأقل حرفين';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // اسم المورد
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'اسم المورد *',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.business),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'يرجى إدخال اسم المورد';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // البريد الإلكتروني
              TextFormField(
                controller: _emailController,
                decoration: const InputDecoration(
                  labelText: 'البريد الإلكتروني',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.email),
                ),
                keyboardType: TextInputType.emailAddress,
                validator: (value) {
                  if (value != null && value.isNotEmpty) {
                    if (!value.contains('@')) {
                      return 'يرجى إدخال بريد إلكتروني صحيح';
                    }
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // الهاتف والجوال
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _phoneController,
                      decoration: const InputDecoration(
                        labelText: 'الهاتف',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.phone),
                      ),
                      keyboardType: TextInputType.phone,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: TextFormField(
                      controller: _mobileController,
                      decoration: const InputDecoration(
                        labelText: 'الجوال',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.smartphone),
                      ),
                      keyboardType: TextInputType.phone,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // العنوان
              TextFormField(
                controller: _streetController,
                decoration: const InputDecoration(
                  labelText: 'الشارع',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.location_on),
                ),
              ),
              const SizedBox(height: 16),

              // المدينة والدولة
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _cityController,
                      decoration: const InputDecoration(
                        labelText: 'المدينة',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.location_city),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _selectedCountry,
                      decoration: const InputDecoration(
                        labelText: 'الدولة',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.flag),
                      ),
                      items: _countries.map((country) {
                        return DropdownMenuItem(
                          value: country,
                          child: Text(country),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _selectedCountry = value);
                        }
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // الرقم الضريبي
              TextFormField(
                controller: _taxNumberController,
                decoration: const InputDecoration(
                  labelText: 'الرقم الضريبي',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.receipt),
                ),
              ),
              const SizedBox(height: 16),

              // الحد الائتماني والعملة
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _creditLimitController,
                      decoration: const InputDecoration(
                        labelText: 'الحد الائتماني',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.credit_card),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) {
                        if (value != null && value.isNotEmpty) {
                          final v = parseMoney(value);
                          if (v == null) {
                            return 'يرجى إدخال رقم صحيح';
                          }
                          if (v < Decimal.zero) {
                            return 'الحد الائتماني لا يمكن أن يكون سالباً';
                          }
                        }
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _selectedCurrency,
                      decoration: const InputDecoration(
                        labelText: 'العملة',
                        border: OutlineInputBorder(),
                      ),
                      items: _currencies.map((currency) {
                        return DropdownMenuItem(
                          value: currency,
                          child: Text(currency),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _selectedCurrency = value);
                        }
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // الحالة
              DropdownButtonFormField<String>(
                value: _selectedStatus,
                decoration: const InputDecoration(
                  labelText: 'الحالة',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.info),
                ),
                items: _statuses.map((status) {
                  return DropdownMenuItem(
                    value: status,
                    child: Row(
                      children: [
                        Container(
                          width: 12,
                          height: 12,
                          decoration: BoxDecoration(
                            color: _getStatusColor(status),
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(_getStatusText(status)),
                      ],
                    ),
                  );
                }).toList(),
                onChanged: (value) {
                  if (value != null) {
                    setState(() => _selectedStatus = value);
                  }
                },
              ),
              const SizedBox(height: 16),

              // ملاحظات
              TextFormField(
                controller: _notesController,
                decoration: const InputDecoration(
                  labelText: 'ملاحظات',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.note),
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 24),

              // زر الحفظ
              AppButton(
                onPressed: _isLoading ? null : _saveSupplier,
                loading: _isLoading,
                expanded: true,
                icon: _isEditing ? Icons.update : Icons.add,
                label: _isEditing ? 'تحديث المورد' : 'إضافة المورد',
                variant: AppButtonVariant.success,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'active':
        return AppColors.success;
      case 'inactive':
        return Colors.grey;
      case 'suspended':
        return AppColors.warning;
      case 'blocked':
        return AppColors.danger;
      default:
        return Colors.grey;
    }
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'active':
        return 'نشط';
      case 'inactive':
        return 'غير نشط';
      case 'suspended':
        return 'معلق';
      case 'blocked':
        return 'محظور';
      default:
        return status;
    }
  }

  Future<void> _deleteSupplier() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف المورد "${widget.supplier?.name}"؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('حذف'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      if (mounted) setState(() => _isLoading = true);
      try {
        final success = await SupplierRepository.deleteSupplier(widget.supplier!.id);
        if (mounted) setState(() => _isLoading = false);

        if (success) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('تم حذف المورد بنجاح'),
                backgroundColor: AppColors.success,
              ),
            );
            Navigator.pop(context, true);
          }
        } else {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('فشل في حذف المورد'),
                backgroundColor: AppColors.danger,
              ),
            );
          }
        }
      } catch (e) {
        if (mounted) setState(() => _isLoading = false);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(ErrorUtils.sanitize(e)),
              backgroundColor: AppColors.danger,
            ),
          );
        }
      }
    }
  }
}