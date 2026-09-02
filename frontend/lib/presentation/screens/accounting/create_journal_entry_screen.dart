import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../providers/accounting_provider.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';

class CreateJournalEntryScreen extends StatefulWidget {
  const CreateJournalEntryScreen({super.key});

  @override
  State<CreateJournalEntryScreen> createState() => _CreateJournalEntryScreenState();
}

class _CreateJournalEntryScreenState extends State<CreateJournalEntryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _descriptionController = TextEditingController();
  final _dateController = TextEditingController();
  final ApiService _api = ApiService();

  DateTime _selectedDate = DateTime.now();
  List<JournalLineData> _lines = [];
  bool _isSaving = false;
  Map<String, dynamic>? _currentPeriod;
  bool _dateOutsidePeriod = false;

  Decimal get _totalDebit => _lines.fold(Decimal.zero, (sum, line) => sum + line.debit);
  Decimal get _totalCredit => _lines.fold(Decimal.zero, (sum, line) => sum + line.credit);
  bool get _isBalanced => (_totalDebit - _totalCredit).abs() < Decimal.parse('0.01');

  @override
  void initState() {
    super.initState();
    _dateController.text = DateFormat('yyyy-MM-dd').format(_selectedDate);
    _addLine();
    _addLine();
    _loadAccounts();
    _loadFiscalPeriods();
  }

  @override
  void dispose() {
    for (final line in _lines) {
      line.dispose();
    }
    _descriptionController.dispose();
    _dateController.dispose();
    super.dispose();
  }

  Future<void> _loadAccounts() async {
    await context.read<AccountingProvider>().loadAccounts();
  }

  Future<void> _loadFiscalPeriods() async {
    try {
      final response = await _api.get('fiscal-periods');
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      final periods = (items as List).cast<Map<String, dynamic>>();
      final today = DateTime.now();
      final openPeriods = periods.where((p) {
        final status = (p['status'] ?? '').toString().toLowerCase();
        if (status != 'open') return false;
        final start = DateTime.tryParse(p['start_date'] ?? '');
        final end = DateTime.tryParse(p['end_date'] ?? '');
        if (start == null || end == null) return false;
        return !today.isBefore(start) && !today.isAfter(end);
      }).toList();
      setState(() {
        _currentPeriod = openPeriods.isNotEmpty ? openPeriods.first : null;
        _dateOutsidePeriod = _isOutsideOpenPeriod(_selectedDate);
      });
    } catch (_) {}
  }

  bool _isOutsideOpenPeriod(DateTime date) {
    final period = _currentPeriod;
    if (period == null) return true;
    final start = DateTime.tryParse(period['start_date'] ?? '');
    final end = DateTime.tryParse(period['end_date'] ?? '');
    if (start == null || end == null) return true;
    return date.isBefore(start) || date.isAfter(end);
  }

  Widget _buildFiscalPeriodBanner() {
    final period = _currentPeriod;
    final isOpen = period != null;
    final String text;
    if (isOpen) {
      final start = DateTime.tryParse(period['start_date'] ?? '');
      final end = DateTime.tryParse(period['end_date'] ?? '');
      text = 'الفترة المالية الحالية: ${period['name']} '
          '(${start != null ? DateFormat('yyyy-MM-dd').format(start) : '-'} - '
          '${end != null ? DateFormat('yyyy-MM-dd').format(end) : '-'})';
    } else {
      text = 'لا توجد فترة مالية مفتوحة حالياً';
    }
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: isOpen ? AppColors.successContainer : AppColors.errorContainer,
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        border: Border.all(color: isOpen ? AppColors.success : AppColors.danger),
      ),
      child: Row(
        children: [
          Icon(
            isOpen ? Icons.check_circle : Icons.error,
            color: isOpen ? AppColors.success : AppColors.danger,
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                color: isOpen ? AppColors.success : AppColors.danger,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _addLine() {
    setState(() {
      _lines.add(JournalLineData());
    });
  }

  void _removeLine(int index) {
    if (_lines.length <= 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('يجب أن يكون هناك سطرين على الأقل'),
          backgroundColor: AppColors.warning,
        ),
      );
      return;
    }
    
    setState(() {
      _lines[index].dispose();
      _lines.removeAt(index);
    });
  }

  Future<void> _selectDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    
    if (picked != null) {
      setState(() {
        _selectedDate = picked;
        _dateController.text = DateFormat('yyyy-MM-dd').format(picked);
        _dateOutsidePeriod = _isOutsideOpenPeriod(picked);
      });
    }
  }

  Future<void> _save({bool post = false}) async {
    if (!_formKey.currentState!.validate()) return;

    if (!_isBalanced) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '❌ القيد غير متوازن\nمدين: ${_totalDebit.toStringAsFixed(2)}\nدائن: ${_totalCredit.toStringAsFixed(2)}',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);

    try {
      final lines = _lines.map((line) => {
        'account_code': line.accountCode,
        'debit': line.debit.toString(),
        'credit': line.credit.toString(),
        if (line.description.isNotEmpty) 'description': line.description,
      }).toList();

      final success = await context.read<AccountingProvider>().createJournalEntry(
        date: _selectedDate,
        description: _descriptionController.text.trim(),
        lines: lines,
      );

      if (success && mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(post ? '✅ تم إنشاء وترحيل القيد بنجاح' : '✅ تم حفظ القيد كمسودة'),
            backgroundColor: AppColors.success,
          ),
        );
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ فشل في حفظ القيد: ${ErrorUtils.sanitize(context.read<AccountingProvider>().error)}'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ ${ErrorUtils.sanitize(e)}'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('قيد يومي جديد'),
        elevation: 0,
      ),
      body: Form(
        key: _formKey,
        child: Column(
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _buildFiscalPeriodBanner(),
                  TextFormField(
                    controller: _dateController,
                    readOnly: true,
                    onTap: _selectDate,
                    decoration: const InputDecoration(
                      labelText: 'التاريخ',
                      prefixIcon: Icon(Icons.calendar_today),
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'الرجاء اختيار التاريخ';
                      }
                      return null;
                    },
                  ),
                  if (_dateOutsidePeriod)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Row(
                        children: const [
                          Icon(Icons.warning_amber_rounded, color: AppColors.warning, size: 18),
                          SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              '⚠️ التاريخ خارج الفترة المالية المفتوحة الحالية',
                              style: TextStyle(color: AppColors.warning, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 16),
                  
                  TextFormField(
                    controller: _descriptionController,
                    decoration: const InputDecoration(
                      labelText: 'البيان',
                      hintText: 'أدخل وصف القيد',
                      prefixIcon: Icon(Icons.description),
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 2,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'الرجاء إدخال البيان';
                      }
                      if (value.trim().length < 3) {
                        return 'البيان يجب أن يكون 3 أحرف على الأقل';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),
                  
                  Row(
                    children: [
                      const Text(
                        'الأسطر المحاسبية',
                        style: AppTextStyles.headlineSmall,
                      ),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: _addLine,
                        icon: const Icon(Icons.add),
                        label: const Text('إضافة سطر'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  
                  ..._lines.asMap().entries.map((entry) {
                    final index = entry.key;
                    final line = entry.value;
                    return _buildLineItem(index, line);
                  }),
                  const SizedBox(height: 24),
                  
                  _buildSummaryCard(),
                ],
              ),
            ),
            
            Container(
              padding: const EdgeInsets.all(AppDimens.s3),
              decoration: BoxDecoration(
                color: AppColors.cardBackground,
                boxShadow: AppDimens.cardShadow,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _isSaving ? null : () => _save(post: false),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: const Text('حفظ كمسودة'),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _isSaving ? null : () => _save(post: true),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        backgroundColor: _isBalanced ? AppColors.success : Colors.grey,
                      ),
                      child: _isSaving
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('حفظ وترحيل'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLineItem(int index, JournalLineData line) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(AppDimens.s3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 14,
                  child: Text('${index + 1}'),
                ),
                const SizedBox(width: 8),
                Text(
                  'سطر ${index + 1}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                IconButton(
                  onPressed: () => _removeLine(index),
                  icon: const Icon(Icons.delete, color: AppColors.danger),
                  iconSize: 20,
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            Consumer<AccountingProvider>(
              builder: (context, provider, child) {
                return DropdownButtonFormField<String>(
                  value: line.accountCode.isNotEmpty ? line.accountCode : null,
                  decoration: const InputDecoration(
                    labelText: 'الحساب',
                    border: OutlineInputBorder(),
                  ),
                  items: provider.accounts.map((account) {
                    return DropdownMenuItem(
                      value: account.code,
                      child: Text('${account.code} - ${account.name}'),
                    );
                  }).toList(),
                  onChanged: (value) {
                    setState(() {
                      _lines[index].accountCode = value ?? '';
                    });
                  },
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'الرجاء اختيار الحساب';
                    }
                    return null;
                  },
                );
              },
            ),
            const SizedBox(height: 12),
            
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: line.debitController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'مدين',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.arrow_downward),
                    ),
                    onChanged: (value) {
                      setState(() {
                        _lines[index].debit = parseMoney(value) ?? Decimal.zero;
                        if (_lines[index].debit > Decimal.zero) {
                          _lines[index].credit = Decimal.zero;
                          line.creditController.clear();
                        }
                      });
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: line.creditController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'دائن',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.arrow_upward),
                    ),
                    onChanged: (value) {
                      setState(() {
                        _lines[index].credit = parseMoney(value) ?? Decimal.zero;
                        if (_lines[index].credit > Decimal.zero) {
                          _lines[index].debit = Decimal.zero;
                          line.debitController.clear();
                        }
                      });
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            TextFormField(
              controller: line.descriptionController,
              decoration: const InputDecoration(
                labelText: 'الوصف (اختياري)',
                border: OutlineInputBorder(),
              ),
              onChanged: (value) {
                _lines[index].description = value;
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard() {
    return Container(
      padding: const EdgeInsets.all(AppDimens.s3),
      decoration: BoxDecoration(
        color: _isBalanced ? AppColors.successContainer : AppColors.errorContainer,
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        border: Border.all(
          color: _isBalanced ? AppColors.success : AppColors.danger,
        ),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('إجمالي المدين:'),
              Text(
                _totalDebit.toStringAsFixed(2),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('إجمالي الدائن:'),
              Text(
                _totalCredit.toStringAsFixed(2),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const Divider(),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'الفرق:',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: _isBalanced ? AppColors.success : AppColors.danger,
                ),
              ),
              Text(
                (_totalDebit - _totalCredit).toStringAsFixed(2),
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: _isBalanced ? AppColors.success : AppColors.danger,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Icon(
            _isBalanced ? Icons.check_circle : Icons.error,
            color: _isBalanced ? AppColors.success : AppColors.danger,
            size: 32,
          ),
          Text(
            _isBalanced ? 'القيد متوازن' : 'القيد غير متوازن',
            style: TextStyle(
              color: _isBalanced ? AppColors.success : AppColors.danger,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

class JournalLineData {
  String accountCode = '';
  Decimal debit = Decimal.zero;
  Decimal credit = Decimal.zero;
  String description = '';

  final TextEditingController debitController = TextEditingController();
  final TextEditingController creditController = TextEditingController();
  final TextEditingController descriptionController = TextEditingController();

  void dispose() {
    debitController.dispose();
    creditController.dispose();
    descriptionController.dispose();
  }
}
