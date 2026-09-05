import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../../data/models/customer_model.dart';
import '../../../data/repositories/customer_repository.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../utils/currency_helper.dart';

class CustomerFormScreen extends StatefulWidget {
  final Customer? customer;
  final String? customerId;

  const CustomerFormScreen({super.key, this.customer, this.customerId});

  @override
  State<CustomerFormScreen> createState() => _CustomerFormScreenState();
}

class _CustomerFormScreenState extends State<CustomerFormScreen> {
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

  final Map<String, String> _countryLabels = {
    'LB': 'لبنان', 'US': 'الولايات المتحدة', 'UK': 'المملكة المتحدة',
    'FR': 'فرنسا', 'AE': 'الإمارات', 'SA': 'السعودية',
  };
  final List<String> _countries = ['LB', 'US', 'UK', 'FR', 'AE', 'SA'];
  
  final Map<String, String> _statusLabels = {
    'active': 'نشط', 'inactive': 'غير نشط', 'suspended': 'معلّق', 'blocked': 'محظور',
  };
  final List<String> _statuses = ['active', 'inactive', 'suspended', 'blocked'];

  @override
  void initState() {
    super.initState();
    _loadCurrencies();
    _isEditing = widget.customer != null || (widget.customerId != null && widget.customerId!.isNotEmpty);
    if (widget.customer != null) {
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
      final customer = await CustomerRepository.getCustomer(widget.customerId!);
      if (customer != null) {
        _fillFromCustomer(customer);
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('العميل غير موجود'), backgroundColor: AppColors.danger),
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

  void _fillFromCustomer(Customer customer) {
    _codeController.text = customer.code;
    _nameController.text = customer.name;
    _emailController.text = customer.email ?? '';
    _phoneController.text = customer.phone ?? '';
    _mobileController.text = customer.mobile ?? '';
    _streetController.text = customer.street ?? '';
    _cityController.text = customer.city ?? '';
    _taxNumberController.text = customer.taxNumber ?? '';
    _creditLimitController.text = customer.creditLimit.toString();
    _notesController.text = customer.notes ?? '';
    _selectedCountry = customer.country;
    _selectedCurrency = customer.currency;
    _selectedStatus = customer.status;
  }

  void _fillForm() {
    final customer = widget.customer!;
    _codeController.text = customer.code;
    _nameController.text = customer.name;
    _emailController.text = customer.email ?? '';
    _phoneController.text = customer.phone ?? '';
    _mobileController.text = customer.mobile ?? '';
    _streetController.text = customer.street ?? '';
    _cityController.text = customer.city ?? '';
    _taxNumberController.text = customer.taxNumber ?? '';
    _creditLimitController.text = customer.creditLimit.toString();
    _notesController.text = customer.notes ?? '';
    _selectedCountry = customer.country;
    _selectedCurrency = customer.currency;
    _selectedStatus = customer.status;
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

  Future<void> _saveCustomer() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final customer = Customer(
        id: widget.customer?.id ?? '',
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
        createdAt: widget.customer?.createdAt ?? DateTime.now(),
        updatedAt: DateTime.now(),
        version: widget.customer?.version ?? 1,
      );

      Customer? result;
      if (_isEditing) {
        result = await CustomerRepository.updateCustomer(customer);
      } else {
        result = await CustomerRepository.createCustomer(customer);
      }

      if (result != null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(_isEditing ? 'تم تحديث العميل بنجاح' : 'تم إنشاء العميل بنجاح'),
            ),
          );
          Navigator.pop(context, true);
        }
      } else {
        throw Exception('فشل في حفظ البيانات');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ErrorUtils.sanitize(e))),
      );
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
        title: Text(_isEditing ? 'تعديل عميل' : 'إضافة عميل جديد'),
        centerTitle: true,
        actions: [
          if (_isEditing)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () => _deleteCustomer(),
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDimens.s3),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // كود العميل
              TextFormField(
                controller: _codeController,
                decoration: const InputDecoration(
                  labelText: 'كود العميل *',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'يرجى إدخال كود العميل';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // اسم العميل
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'اسم العميل *',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'يرجى إدخال اسم العميل';
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
                ),
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: 16),

              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _phoneController,
                      decoration: const InputDecoration(
                        labelText: 'الهاتف',
                        border: OutlineInputBorder(),
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
                ),
              ),
              const SizedBox(height: 16),

              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _cityController,
                      decoration: const InputDecoration(
                        labelText: 'المدينة',
                        border: OutlineInputBorder(),
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
                      ),
                      items: _countries.map((country) {
                        return DropdownMenuItem(
                          value: country,
                          child: Text(_countryLabels[country] ?? country),
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
                ),
              ),
              const SizedBox(height: 16),

              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _creditLimitController,
                      decoration: const InputDecoration(
                        labelText: 'الحد الائتماني',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) {
                        if (value != null && value.isNotEmpty) {
                          if (double.tryParse(value) == null) {
                            return 'يرجى إدخال رقم صحيح';
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
                ),
                items: _statuses.map((status) {
                  return DropdownMenuItem(
                    value: status,
                    child: Text(_statusLabels[status] ?? status),
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
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 24),

              // زر الحفظ
              AppButton(
                label: _isEditing ? 'تحديث' : 'إضافة',
                onPressed: _isLoading ? null : _saveCustomer,
                variant: AppButtonVariant.success,
                loading: _isLoading,
                expanded: true,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _deleteCustomer() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف العميل "${widget.customer?.name}"؟'),
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
      final success = await CustomerRepository.deleteCustomer(widget.customer!.id);
      if (mounted) {
        setState(() => _isLoading = false);
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('تم حذف العميل بنجاح')),
          );
          Navigator.pop(context, true);
        }
      }
    }
  }
}