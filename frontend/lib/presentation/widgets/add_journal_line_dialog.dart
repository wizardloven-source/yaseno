// C:\Users\MTC\yaseeno\frontend\lib\presentation\widgets\add_journal_line_dialog.dart

import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../utils/money_utils.dart';
import '../../utils/currency_helper.dart';

class AddJournalLineDialog extends StatefulWidget {
  const AddJournalLineDialog({super.key});

  @override
  State<AddJournalLineDialog> createState() => _AddJournalLineDialogState();
}

class _AddJournalLineDialogState extends State<AddJournalLineDialog> {
  final _formKey = GlobalKey<FormState>();
  final _accountController = TextEditingController();
  final _debitController = TextEditingController();
  final _creditController = TextEditingController();
  final _descriptionController = TextEditingController();
  String _selectedCurrency = 'USD';
  bool _isDebit = true;
  List<Map<String, dynamic>> _currencies = [];

  @override
  void initState() {
    super.initState();
    _loadCurrencies();
  }

  Future<void> _loadCurrencies() async {
    await CurrencyHelper.load();
    if (mounted) {
      setState(() {
        _currencies = CurrencyHelper.currencies;
        if (_currencies.isNotEmpty && !_currencies.any((c) => c['code'] == _selectedCurrency)) {
          _selectedCurrency = CurrencyHelper.baseCurrency;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.add_circle_outline, color: Colors.blue),
          SizedBox(width: 8),
          Text('إضافة بند قيد'),
        ],
      ),
      content: SizedBox(
        width: 450,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // ========== كود الحساب ==========
              TextFormField(
                controller: _accountController,
                decoration: const InputDecoration(
                  labelText: 'كود الحساب',
                  hintText: 'مثال: 1010',
                  prefixIcon: Icon(Icons.account_balance),
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'الرجاء إدخال كود الحساب';
                  }
                  if (!RegExp(r'^[0-9]+$').hasMatch(value)) {
                    return 'كود الحساب يجب أن يكون أرقاماً فقط';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 12),

              // ========== الوصف ==========
              TextFormField(
                controller: _descriptionController,
                decoration: const InputDecoration(
                  labelText: 'وصف البند (اختياري)',
                  prefixIcon: Icon(Icons.description),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),

              // ========== نوع الحركة (مدين/دائن) ==========
              Row(
                children: [
                  Expanded(
                    child: SegmentedButton<bool>(
                      segments: const [
                        ButtonSegment(
                          value: true,
                          icon: Icon(Icons.arrow_upward, color: Colors.green),
                          label: Text('مدين'),
                        ),
                        ButtonSegment(
                          value: false,
                          icon: Icon(Icons.arrow_downward, color: Colors.red),
                          label: Text('دائن'),
                        ),
                      ],
                      selected: {_isDebit},
                      onSelectionChanged: (Set<bool> newSelection) {
                        setState(() {
                          _isDebit = newSelection.first;
                        });
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // ========== المبلغ ==========
              TextFormField(
                controller: _isDebit ? _debitController : _creditController,
                decoration: InputDecoration(
                  labelText: _isDebit ? 'المبلغ (مدين)' : 'المبلغ (دائن)',
                  prefixIcon: Icon(
                    _isDebit ? Icons.trending_up : Icons.trending_down,
                    color: _isDebit ? Colors.green : Colors.red,
                  ),
                  border: const OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'الرجاء إدخال المبلغ';
                  }
                  if (parseMoney(value) == null) {
                    return 'الرجاء إدخال رقم صحيح';
                  }
                  if (parseMoneyOrZero(value) <= Decimal.zero) {
                    return 'المبلغ يجب أن يكون أكبر من صفر';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 12),

              // ========== العملة ==========
              DropdownButtonFormField<String>(
                value: _selectedCurrency,
                decoration: const InputDecoration(
                  labelText: 'العملة',
                  prefixIcon: Icon(Icons.currency_exchange),
                  border: OutlineInputBorder(),
                ),
                items: _currencies.map((c) => DropdownMenuItem<String>(
                  value: (c['code'] ?? '').toString(),
                  child: Text('${c['code'] ?? ''} ${c['symbol'] != null ? "- ${c['symbol']}" : ''}'),
                )).toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedCurrency = value!;
                  });
                },
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('إلغاء'),
        ),
        ElevatedButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              final amount = parseMoneyOrZero(
                _isDebit ? _debitController.text : _creditController.text,
              );
              Navigator.pop(context, {
                'account_code': _accountController.text,
                'debit': _isDebit ? amount.toDouble() : 0,
                'credit': _isDebit ? 0 : amount.toDouble(),
                'currency': _selectedCurrency,
                'description': _descriptionController.text,
              });
            }
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.blue.shade700,
            foregroundColor: Colors.white,
          ),
          child: const Text('إضافة'),
        ),
      ],
    );
  }

  @override
  void dispose() {
    _accountController.dispose();
    _debitController.dispose();
    _creditController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }
}