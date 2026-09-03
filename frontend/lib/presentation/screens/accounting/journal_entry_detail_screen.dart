import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:decimal/decimal.dart';
import '../../../services/api_service.dart';
import '../../../services/api_client.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/status_chip.dart';

class JournalEntryDetailScreen extends StatefulWidget {
  final String entryId;

  const JournalEntryDetailScreen({super.key, required this.entryId});

  @override
  State<JournalEntryDetailScreen> createState() => _JournalEntryDetailScreenState();
}

class _JournalEntryDetailScreenState extends State<JournalEntryDetailScreen> {
  final ApiService _api = ApiService();
  Map<String, dynamic>? _entry;
  bool _isLoading = true;
  String? _error;
  String _currencySymbol = 'د.ع';

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
    _loadEntry();
  }

  Future<void> _loadBaseCurrency() async {
    try {
      final res = await _api.get('currency/base');
      final data = res['data'];
      if (data is Map && mounted) {
        setState(() => _currencySymbol = data['symbol'] ?? 'د.ع');
      }
    } catch (_) {}
  }

  Future<void> _loadEntry() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('journal-entries/${widget.entryId}');
      setState(() {
        _entry = response['data'] ?? response;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _postEntry() async {
    try {
      await _api.post('journal-entries/${widget.entryId}/post');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم ترحيل القيد بنجاح'), backgroundColor: AppColors.success),
        );
        _loadEntry();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Future<void> _reverseEntry() async {
    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('عكس القيد'),
        content: TextField(
          autofocus: true,
          decoration: const InputDecoration(hintText: 'سبب العكس', border: OutlineInputBorder()),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('إلغاء')),
          TextButton(onPressed: () => Navigator.pop(ctx, ' '), child: const Text('عكس')),
        ],
      ),
    );
    if (reason == null) return;
    try {
      final dio = ApiClient().dio;
      await dio.post(
        '/journal-entries/${widget.entryId}/reverse',
        queryParameters: {'reason': reason.trim()},
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم عكس القيد بنجاح'), backgroundColor: AppColors.warning),
        );
        _loadEntry();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('تفاصيل القيد #${widget.entryId.substring(0, 8)}'),
        centerTitle: true,
        actions: [
          if (_entry != null && _entry!['is_posted'] == false) ...[
            IconButton(
              icon: const Icon(Icons.send, color: AppColors.success),
              onPressed: _postEntry,
              tooltip: 'ترحيل',
            ),
            IconButton(
              icon: const Icon(Icons.undo, color: AppColors.warning),
              onPressed: _reverseEntry,
              tooltip: 'عكس',
            ),
          ],
        ],
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadEntry, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const LoadingState();
    if (_entry == null) return const EmptyState(
      icon: Icons.receipt_long_outlined,
      title: 'القيد غير موجود',
    );

    final lines = (_entry!['lines'] ?? []) as List;
    final totalDebit = parseMoney(_entry!['total_debit']) ?? Decimal.zero;
    final totalCredit = parseMoney(_entry!['total_credit']) ?? Decimal.zero;
    final isPosted = _entry!['is_posted'] ?? false;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppDimens.s3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppDimens.s3),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      StatusChip(status: isPosted ? 'posted' : 'draft'),
                      const Spacer(),
                      if (_entry!['number'] != null)
                        Text('#${_entry!['number']}', style: Theme.of(context).textTheme.titleMedium),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _infoRow('التاريخ', _entry!['date'] ?? ''),
                  _infoRow('الوصف', _entry!['description'] ?? ''),
                  if (_entry!['notes'] != null) _infoRow('ملاحظات', _entry!['notes']),
                  _infoRow('الإصدار', '${_entry!['version'] ?? 1}'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text('بنود القيد', style: AppTextStyles.headlineSmall),
          const SizedBox(height: 8),
          Card(
            child: DataTable(
              columns: const [
                DataColumn(label: Text('الحساب')),
                DataColumn(label: Text('الوصف'), numeric: false),
                DataColumn(label: Text('مدين'), numeric: true),
                DataColumn(label: Text('دائن'), numeric: true),
              ],
              rows: lines.map((line) {
                return DataRow(cells: [
                  DataCell(Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text('${line['account_code'] ?? ''}',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      if (line['account_name'] != null && line['account_name'].toString().isNotEmpty)
                        Text('${line['account_name']}',
                            style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                    ],
                  )),
                  DataCell(Text('${line['description'] ?? ''}', style: const TextStyle(fontSize: 12))),
                  DataCell(Text(
                    (parseMoney(line['debit']) ?? Decimal.zero) > Decimal.zero
                        ? formatMoneyCurrency(line['debit'], currency: _currencySymbol)
                        : '-',
                    style: const TextStyle(fontWeight: FontWeight.w500),
                  )),
                  DataCell(Text(
                    (parseMoney(line['credit']) ?? Decimal.zero) > Decimal.zero
                        ? formatMoneyCurrency(line['credit'], currency: _currencySymbol)
                        : '-',
                    style: const TextStyle(fontWeight: FontWeight.w500),
                  )),
                ]);
              }).toList(),
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(AppDimens.s3),
            decoration: BoxDecoration(
              color: AppColors.primaryContainer,
              borderRadius: BorderRadius.circular(AppDimens.radiusCard),
            ),
            child: Row(
              children: [
                Text('إجمالي مدين: ${formatMoneyCurrency(totalDebit, currency: _currencySymbol)}',
                    style: const TextStyle(fontWeight: FontWeight.bold)),
                const Spacer(),
                Text('إجمالي دائن: ${formatMoneyCurrency(totalCredit, currency: _currencySymbol)}',
                    style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(width: 12),
                Icon(
                  (totalDebit - totalCredit).abs() < Decimal.parse('0.01') ? Icons.check_circle : Icons.error,
                  color: (totalDebit - totalCredit).abs() < Decimal.parse('0.01') ? AppColors.success : AppColors.danger,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text('$label:', style: const TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w500)),
          ),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500))),
        ],
      ),
    );
  }
}
