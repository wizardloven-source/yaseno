import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../../data/models/product_model.dart';
import '../../../data/repositories/product_repository.dart';
import '../../widgets/loading_widget.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../widgets/app_widgets.dart';
import '../../../utils/currency_helper.dart';

class ProductFormScreen extends StatefulWidget {
  final Product? product;
  final String? productId;

  const ProductFormScreen({super.key, this.product, this.productId});

  @override
  State<ProductFormScreen> createState() => _ProductFormScreenState();
}

class _ProductFormScreenState extends State<ProductFormScreen> {
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;
  bool _isEditing = false;

  // Controllers
  final _codeController = TextEditingController();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _categoryController = TextEditingController();
  final _unitPriceController = TextEditingController();
  final _taxRateController = TextEditingController();
  final _stockQuantityController = TextEditingController();

  String _selectedCurrency = 'USD';
  bool _isActive = true;
  List<String> _currencies = [];
  final List<String> _categories = [
    'إلكترونيات',
    'ملابس',
    'أثاث',
    'مواد غذائية',
    'مواد بناء',
    'أدوات مكتبية',
    'خدمات',
    'أخرى',
  ];

  @override
  void initState() {
    super.initState();
    _loadCurrencies();
    _isEditing = widget.product != null || (widget.productId != null && widget.productId!.isNotEmpty);
    if (widget.product != null) {
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
      final product = await ProductRepository.getProduct(widget.productId!);
      if (product != null) {
        _fillFromProduct(product);
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('المنتج غير موجود'), backgroundColor: AppColors.danger),
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

  void _fillFromProduct(Product product) {
    _codeController.text = product.code;
    _nameController.text = product.name;
    _descriptionController.text = product.description ?? '';
    _categoryController.text = product.category ?? '';
    _unitPriceController.text = formatMoney(product.unitPrice);
    _taxRateController.text = formatMoney(product.taxRate);
    _stockQuantityController.text = product.stockQuantity.toString();
    _selectedCurrency = product.currency;
    _isActive = product.isActive;
  }

  void _fillForm() {
    final product = widget.product!;
    _codeController.text = product.code;
    _nameController.text = product.name;
    _descriptionController.text = product.description ?? '';
    _categoryController.text = product.category ?? '';
    _unitPriceController.text = formatMoney(product.unitPrice);
    _taxRateController.text = formatMoney(product.taxRate);
    _stockQuantityController.text = product.stockQuantity.toString();
    _selectedCurrency = product.currency;
    _isActive = product.isActive;
  }

  @override
  void dispose() {
    _codeController.dispose();
    _nameController.dispose();
    _descriptionController.dispose();
    _categoryController.dispose();
    _unitPriceController.dispose();
    _taxRateController.dispose();
    _stockQuantityController.dispose();
    super.dispose();
  }

  Future<void> _saveProduct() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final product = Product(
        id: widget.product?.id ?? '',
        code: _codeController.text,
        name: _nameController.text,
        description: _descriptionController.text.isNotEmpty ? _descriptionController.text : null,
        category: _categoryController.text.isNotEmpty ? _categoryController.text : null,
        unitPrice: parseMoney(_unitPriceController.text) ?? Decimal.zero,
        currency: _selectedCurrency,
        taxRate: parseMoney(_taxRateController.text) ?? Decimal.zero,
        stockQuantity: int.tryParse(_stockQuantityController.text) ?? 0,
        isActive: _isActive,
        createdAt: widget.product?.createdAt ?? DateTime.now(),
        updatedAt: DateTime.now(),
        version: widget.product?.version ?? 1,
      );

      Product? result;
      if (_isEditing) {
        result = await ProductRepository.updateProduct(product);
      } else {
        result = await ProductRepository.createProduct(product);
      }

      if (result != null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(_isEditing ? 'تم تحديث المنتج بنجاح' : 'تم إنشاء المنتج بنجاح'),
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
        body: LoadingWidget(),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_isEditing ? 'تعديل منتج' : 'إضافة منتج جديد'),
        centerTitle: true,
        actions: [
          if (_isEditing)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () => _deleteProduct(),
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
              // كود المنتج
              TextFormField(
                controller: _codeController,
                decoration: const InputDecoration(
                  labelText: 'كود المنتج *',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.code),
                  helperText: 'مثال: P001',
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'يرجى إدخال كود المنتج';
                  }
                  if (value.length < 2) {
                    return 'الكود يجب أن يكون على الأقل حرفين';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // اسم المنتج
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'اسم المنتج *',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.production_quantity_limits),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'يرجى إدخال اسم المنتج';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // الوصف
              TextFormField(
                controller: _descriptionController,
                decoration: const InputDecoration(
                  labelText: 'الوصف',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.description),
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 16),

              // التصنيف
              DropdownButtonFormField<String>(
                value: _categoryController.text.isNotEmpty ? _categoryController.text : null,
                decoration: const InputDecoration(
                  labelText: 'التصنيف',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.category),
                ),
                items: _categories.map((category) {
                  return DropdownMenuItem(
                    value: category,
                    child: Text(category),
                  );
                }).toList(),
                onChanged: (value) {
                  if (value != null) {
                    setState(() => _categoryController.text = value);
                  }
                },
                onSaved: (value) => _categoryController.text = value ?? '',
              ),
              const SizedBox(height: 16),

              // السعر والعملة
              Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: TextFormField(
                      controller: _unitPriceController,
                      decoration: const InputDecoration(
                        labelText: 'سعر الوحدة *',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.attach_money),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'يرجى إدخال السعر';
                        }
                        final price = parseMoney(value);
                        if (price == null || price <= Decimal.zero) {
                          return 'يرجى إدخال سعر صحيح أكبر من صفر';
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

              // نسبة الضريبة
              TextFormField(
                controller: _taxRateController,
                decoration: const InputDecoration(
                  labelText: 'نسبة الضريبة (%)',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.percent),
                  suffixText: '%',
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value != null && value.isNotEmpty) {
                    final tax = parseMoney(value);
                    if (tax != null && (tax < Decimal.zero || tax > Decimal.fromInt(100))) {
                      return 'نسبة الضريبة يجب أن تكون بين 0 و 100';
                    }
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // كمية المخزون
              TextFormField(
                controller: _stockQuantityController,
                decoration: const InputDecoration(
                  labelText: 'كمية المخزون',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.inventory),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value != null && value.isNotEmpty) {
                    final stock = int.tryParse(value);
                    if (stock != null && stock < 0) {
                      return 'كمية المخزون لا يمكن أن تكون سالبة';
                    }
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // الحالة (نشط/غير نشط)
              SwitchListTile(
                title: const Text('المنتج نشط'),
                value: _isActive,
                onChanged: (value) {
                  setState(() => _isActive = value);
                },
                secondary: Icon(
                  _isActive ? Icons.check_circle : Icons.cancel,
                  color: _isActive ? AppColors.success : AppColors.danger,
                ),
                tileColor: _isActive ? AppColors.successContainer : AppColors.surfaceVariant,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              const SizedBox(height: 24),

              // أزرار الحفظ
              Row(
                children: [
                  Expanded(
                    child: AppButton(
                      onPressed: _saveProduct,
                      loading: _isLoading,
                      expanded: true,
                      icon: _isEditing ? Icons.update : Icons.add,
                      label: _isEditing ? 'تحديث المنتج' : 'إضافة المنتج',
                      variant: AppButtonVariant.success,
                    ),
                  ),
                  if (_isEditing) ...[
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.pop(context),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          foregroundColor: AppColors.buttonCancel,
                          side: const BorderSide(color: AppColors.buttonCancel),
                        ),
                        child: const Text('إلغاء'),
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _deleteProduct() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف المنتج "${widget.product?.name}"؟'),
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
        final success = await ProductRepository.deleteProduct(widget.product!.id);
        if (mounted) setState(() => _isLoading = false);

        if (success) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('تم حذف المنتج بنجاح'),
                backgroundColor: AppColors.success,
              ),
            );
            Navigator.pop(context, true);
          }
        } else {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('فشل في حذف المنتج'),
                backgroundColor: AppColors.danger,
              ),
            );
          }
        }
      } catch (e) {
        if (mounted) {
          setState(() => _isLoading = false);
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