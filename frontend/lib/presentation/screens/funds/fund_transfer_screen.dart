import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:decimal/decimal.dart';
import '../../../theme/app_colors.dart';
import '../../providers/funds_provider.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/app_widgets.dart';
import '../../../utils/error_utils.dart';

class FundTransferScreen extends StatefulWidget {
  const FundTransferScreen({super.key});

  @override
  State<FundTransferScreen> createState() => _FundTransferScreenState();
}

class _FundTransferScreenState extends State<FundTransferScreen> {
  final _formKey = GlobalKey<FormState>();

  Map<String, dynamic>? _fromFund;
  Map<String, dynamic>? _toFund;
  String _amount = '';
  String _reason = '';
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<FundsProvider>().loadFunds();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('تحويل بين الصناديق'),
        backgroundColor: AppColors.secondary,
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const LoadingState(skeleton: false)
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildFromFundCard(),
                    const SizedBox(height: 16),
                    _buildToFundCard(),
                    const SizedBox(height: 16),
                    _buildAmountCard(),
                    const SizedBox(height: 16),
                    _buildReasonCard(),
                    const SizedBox(height: 24),
                    if (_fromFund != null && _toFund != null && _amount.isNotEmpty) ...[
                      _buildTransferSummary(),
                      const SizedBox(height: 16),
                    ],
                    AppButton(
                      label: 'تنفيذ التحويل',
                      icon: Icons.swap_horiz,
                      variant: AppButtonVariant.secondary,
                      expanded: true,
                      onPressed: _executeTransfer,
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildFromFundCard() {
    final funds = context.watch<FundsProvider>().funds;
    final fundMaps = funds
        .where((f) => f.isActive && f.id != (_toFund?['id']))
        .map((f) => {
              'id': f.id,
              'code': f.code,
              'name': f.name,
              'balance': f.balance,
              'currency': f.currency,
              'isActive': f.isActive,
            })
        .toList();

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'من صندوق',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: AppColors.danger,
              ),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<Map<String, dynamic>>(
              value: _fromFund,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.account_balance_wallet),
              ),
              items: fundMaps
                  .map((fund) => DropdownMenuItem(
                        value: fund,
                        child: Text('${fund['code']} - ${fund['name']}'),
                      ))
                  .toList(),
              onChanged: (value) => setState(() => _fromFund = value),
              validator: (value) => value == null ? 'اختر صندوق المصدر' : null,
            ),
            if (_fromFund != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Text('الرصيد المتاح:'),
                    const SizedBox(width: 8),
                    Text(
                      '${(_fromFund!['balance'] as Decimal).toStringAsFixed(2)} ${_fromFund!['currency']}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildToFundCard() {
    final funds = context.watch<FundsProvider>().funds;
    final fundMaps = funds
        .where((f) => f.isActive && f.id != (_fromFund?['id']))
        .map((f) => {
              'id': f.id,
              'code': f.code,
              'name': f.name,
              'currency': f.currency,
              'isActive': f.isActive,
            })
        .toList();

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'إلى صندوق',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: AppColors.success,
              ),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<Map<String, dynamic>>(
              value: _toFund,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.account_balance_wallet),
              ),
              items: fundMaps
                  .map((fund) => DropdownMenuItem(
                        value: fund,
                        child: Text('${fund['code']} - ${fund['name']}'),
                      ))
                  .toList(),
              onChanged: (value) => setState(() => _toFund = value),
              validator: (value) => value == null ? 'اختر صندوق الهدف' : null,
            ),
            if (_toFund != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Text('عملة الصندوق:'),
                    const SizedBox(width: 8),
                    Text(
                      _toFund!['currency'] ?? '',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAmountCard() {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'مبلغ التحويل',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: TextFormField(
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'المبلغ',
                      border: const OutlineInputBorder(),
                      prefixIcon: const Icon(Icons.attach_money),
                      suffixText: _fromFund?['currency'] ?? '',
                    ),
                    onChanged: (value) => setState(() => _amount = value),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'المبلغ مطلوب';
                      }
                      final amount = Decimal.tryParse(value);
                      if (amount == null || amount <= Decimal.zero) {
                        return 'المبلغ يجب أن يكون أكبر من صفر';
                      }
                      if (_fromFund != null) {
                        final fromBalance = (_fromFund!['balance'] as Decimal?) ?? Decimal.zero;
                        if (amount > fromBalance) {
                          return 'المبلغ يتجاوز الرصيد المتاح';
                        }
                      }
                      return null;
                    },
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReasonCard() {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'سبب التحويل',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              decoration: const InputDecoration(
                labelText: 'السبب',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.description),
              ),
              maxLines: 2,
              onChanged: (value) => _reason = value,
              validator: (value) =>
                  value == null || value.isEmpty ? 'السبب مطلوب' : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTransferSummary() {
    final amount = Decimal.tryParse(_amount) ?? Decimal.zero;

    return Card(
      elevation: 2,
      color: AppColors.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            const Text(
              'ملخص التحويل',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('من'),
                Text(_fromFund!['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('إلى'),
                Text(_toFund!['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            const Divider(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('المبلغ', style: TextStyle(fontWeight: FontWeight.bold)),
                Text(
                  '${amount.toStringAsFixed(2)} ${_fromFund!['currency'] ?? ''}',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    color: AppColors.secondary,
                  ),
                ),
              ],
            ),
            if ((_fromFund!['currency'] ?? '') != (_toFund!['currency'] ?? '')) ...[
              const SizedBox(height: 4),
              Text(
                'تنبيه: العملات مختلفة (${_fromFund!['currency']} → ${_toFund!['currency']})',
                style: const TextStyle(fontSize: 12, color: AppColors.warning),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _executeTransfer() async {
    if (!_formKey.currentState!.validate()) return;

    final amount = Decimal.tryParse(_amount) ?? Decimal.zero;

    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد التحويل'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('من: ${_fromFund!['name'] ?? ''}'),
            Text('إلى: ${_toFund!['name'] ?? ''}'),
            Text('المبلغ: ${amount.toStringAsFixed(2)} ${_fromFund!['currency'] ?? ''}'),
            const SizedBox(height: 8),
            const Text('هل أنت متأكد من تنفيذ التحويل؟'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.secondary),
            child: const Text('تأكيد'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    setState(() => _isLoading = true);

    try {
      final provider = context.read<FundsProvider>();
      await provider.transferBetweenFunds(
        fromFundId: _fromFund!['id'],
        toFundId: _toFund!['id'],
        amount: amount,
        reason: _reason,
        createdBy: 'system',
      );

      if (mounted) {
        Navigator.pop(context, true);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم التحويل بنجاح'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ErrorUtils.sanitize(e)),
          backgroundColor: AppColors.danger,
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }
}
