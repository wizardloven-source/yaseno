import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_text_styles.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/currency_helper.dart';

class FundListScreen extends StatefulWidget {
  const FundListScreen({super.key});

  @override
  State<FundListScreen> createState() => _FundListScreenState();
}

class _FundListScreenState extends State<FundListScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _funds = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadFunds();
  }

  Future<void> _loadFunds() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('funds');
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _funds = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteFund(String fundId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف الصندوق'),
        content: const Text('هل أنت متأكد من حذف هذا الصندوق؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('حذف', style: TextStyle(color: AppColors.danger))),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final res = await _api.delete('funds/$fundId');
      if (res['success'] == false) {
        throw Exception(res['message'] ?? 'فشل حذف الصندوق');
      }
      _loadFunds();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الصناديق النقدية'),
        centerTitle: true,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadFunds),
        ],
      ),
      body: _buildBody(),
      floatingActionButton: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          FloatingActionButton.extended(
            heroTag: 'transfer',
            onPressed: () async {
              await context.push('/funds/transfer');
              _loadFunds();
            },
            icon: const Icon(Icons.swap_horiz),
            label: const Text('تحويل'),
          ),
          const SizedBox(height: 12),
          FloatingActionButton(
            heroTag: 'add',
            onPressed: () async {
              await context.push('/funds/create');
              _loadFunds();
            },
            child: const Icon(Icons.add),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    return Column(
      children: [
        if (_error != null)
          MaterialBanner(
            content: Text(ErrorUtils.sanitize(_error)),
            leading: const Icon(Icons.wifi_off, color: AppColors.warning),
            actions: [
              TextButton(onPressed: _loadFunds, child: const Text('إعادة المحاولة')),
            ],
            backgroundColor: AppColors.warningContainer,
          ),
        if (_funds.isEmpty && _error == null)
          Expanded(
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.account_balance_wallet_outlined, size: 64, color: Theme.of(context).colorScheme.onSurfaceVariant),
                  const SizedBox(height: 16),
                  Text('لا توجد صناديق', style: AppTextStyles.headlineSmall),
                ],
              ),
            ),
          )
        else if (_funds.isNotEmpty)
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadFunds,
              child: ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: _funds.length,
                itemBuilder: (context, index) {
                  final fund = _funds[index];
                  final status = fund['status'] ?? 'active';
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: status == 'active' ? AppColors.successContainer : Theme.of(context).colorScheme.outlineVariant,
                        child: Icon(Icons.account_balance_wallet,
                            color: status == 'active' ? AppColors.success : Theme.of(context).colorScheme.onSurfaceVariant),
                      ),
                      title: Text('${fund['name'] ?? ''}', style: AppTextStyles.titleMedium),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('الرمز: ${fund['code'] ?? ''}'),
                          Text('العملة: ${fund['currency'] ?? CurrencyHelper.baseCurrency}'),
                          if (fund['fund_type'] != null) Text('النوع: ${fund['fund_type']}'),
                        ],
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.receipt_long),
                            tooltip: 'التفاصيل',
                            onPressed: () async {
                              final fundId = fund['id']?.toString() ?? '';
                              final fundName = '${fund['name'] ?? ''}';
                              await context.push('/funds/$fundId/detail?name=${Uri.encodeComponent(fundName)}');
                              _loadFunds();
                            },
                          ),
                          PopupMenuButton(
                            itemBuilder: (ctx) => [
                              const PopupMenuItem(value: 'edit', child: Text('تعديل')),
                              const PopupMenuItem(value: 'delete', child: Text('حذف', style: TextStyle(color: AppColors.danger))),
                            ],
                            onSelected: (v) async {
                              if (v == 'edit') {
                                await context.push('/funds/${fund['id']}');
                                _loadFunds();
                              } else if (v == 'delete') {
                                _deleteFund(fund['id']);
                              }
                            },
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          )
        else
          const Expanded(child: SizedBox.shrink()),
      ],
    );
  }
}
