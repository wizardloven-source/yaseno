import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import 'package:intl/intl.dart';
import 'package:decimal/decimal.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';

class ApprovalsScreen extends StatefulWidget {
  const ApprovalsScreen({super.key});

  @override
  State<ApprovalsScreen> createState() => _ApprovalsScreenState();
}

class _ApprovalsScreenState extends State<ApprovalsScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _requests = [];
  Map<String, dynamic> _stats = {};
  bool _isLoading = true;
  String? _error;
  String? _filterEntityType;

  bool _selectionMode = false;
  final Set<String> _selectedIds = {};

  final List<String> _entityTypes = [
    'purchase_order',
    'invoice',
    'payment',
    'expense',
    'journal_entry',
  ];

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final params = <String, dynamic>{};
      if (_filterEntityType != null) params['entity_type'] = _filterEntityType;
      final results = await Future.wait([
        _api.get('approval-requests/pending',
            queryParameters: params.isNotEmpty ? params : null),
        _api.get('approval-requests/statistics'),
      ]);
      final listResp = results[0];
      final statsResp = results[1];
      final listData = listResp['data'];
      final listItems = (listData is Map ? listData['items'] : listData) ?? [];
      final statsData = statsResp['data'] ?? statsResp;
      setState(() {
        _requests = (listItems as List).cast<Map<String, dynamic>>();
        _stats = statsData is Map ? statsData.cast<String, dynamic>() : {};
        _isLoading = false;
        _selectedIds.clear();
        _selectionMode = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppColors.danger),
    );
  }

  void _showSuccess(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppColors.success),
    );
  }

  // ── Approve ────────────────────────────────────────────────────────
  Future<void> _approveRequest(String id) async {
    final commentCtrl = TextEditingController();
    final confirmed = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('الموافقة'),
        content: TextField(
          controller: commentCtrl,
          decoration: const InputDecoration(
            labelText: 'تعليق (اختياري)',
            border: OutlineInputBorder(),
          ),
          maxLines: 2,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
          AppButton(
            variant: AppButtonVariant.success,
            label: 'موافقة',
            onPressed: () => Navigator.pop(ctx, commentCtrl.text),
          ),
        ],
      ),
    );
    if (confirmed == null) return;
    try {
      await _api.post('approval-requests/$id/approve',
          data: {'comment': confirmed});
      _showSuccess('تمت الموافقة');
      _loadAll();
    } catch (e) {
      _showError(ErrorUtils.sanitize(e));
    }
  }

  // ── Reject ─────────────────────────────────────────────────────────
  Future<void> _rejectRequest(String id) async {
    final reasonCtrl = TextEditingController();
    final confirmed = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('رفض'),
        content: TextField(
          controller: reasonCtrl,
          decoration: const InputDecoration(
            labelText: 'سبب الرفض',
            border: OutlineInputBorder(),
          ),
          maxLines: 2,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
          AppButton(
            variant: AppButtonVariant.danger,
            label: 'رفض',
            onPressed: () {
              if (reasonCtrl.text.trim().isEmpty) {
                ScaffoldMessenger.of(ctx).showSnackBar(
                  const SnackBar(content: Text('سبب الرفض مطلوب')),
                );
                return;
              }
              Navigator.pop(ctx, reasonCtrl.text);
            },
          ),
        ],
      ),
    );
    if (confirmed == null) return;
    try {
      await _api.post('approval-requests/$id/reject',
          data: {'reason': confirmed});
      _showSuccess('تم الرفض');
      _loadAll();
    } catch (e) {
      _showError(ErrorUtils.sanitize(e));
    }
  }

  // ── Escalate ───────────────────────────────────────────────────────
  Future<void> _escalateRequest(String id) async {
    try {
      await _api.post('approval-requests/$id/escalate');
      _showSuccess('تم التصعيد');
      _loadAll();
    } catch (e) {
      _showError(ErrorUtils.sanitize(e));
    }
  }

  // ── Reassign ───────────────────────────────────────────────────────
  Future<void> _reassignRequest(String id) async {
    List<Map<String, dynamic>> users = [];
    try {
      final resp = await _api.get('auth/users');
      final data = resp['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      users = (items as List).cast<Map<String, dynamic>>();
    } catch (_) {}

    if (!mounted) return;
    final selectedId = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('إعادة التعيين'),
        content: SizedBox(
          width: double.maxFinite,
          height: 300,
          child: users.isEmpty
              ? const Center(child: Text('لا يوجد مستخدمون'))
              : ListView.builder(
                  itemCount: users.length,
                  itemBuilder: (ctx, index) {
                    final u = users[index];
                    final uid = (u['id'] ?? '').toString();
                    final uname =
                        u['username'] ?? u['name'] ?? uid;
                    return ListTile(
                      title: Text(uname),
                      subtitle: Text(u['role'] ?? ''),
                      onTap: () => Navigator.pop(ctx, uid),
                    );
                  },
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
        ],
      ),
    );
    if (selectedId == null) return;
    try {
      await _api.post('approval-requests/$id/reassign',
          data: {'new_approver_id': selectedId});
      _showSuccess('تمت إعادة التعيين');
      _loadAll();
    } catch (e) {
      _showError(ErrorUtils.sanitize(e));
    }
  }

  // ── Batch Approve ──────────────────────────────────────────────────
  Future<void> _batchApprove() async {
    if (_selectedIds.isEmpty) return;
    try {
      await _api.post('approval-requests/batch-approve',
          data: {'request_ids': _selectedIds.toList()});
      _showSuccess('تمت الموافقة على ${_selectedIds.length} طلبات');
      _loadAll();
    } catch (e) {
      _showError(ErrorUtils.sanitize(e));
    }
  }

  // ── Batch Reject ───────────────────────────────────────────────────
  Future<void> _batchReject() async {
    if (_selectedIds.isEmpty) return;
    final reasonCtrl = TextEditingController();
    final confirmed = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('رفض جماعي'),
        content: TextField(
          controller: reasonCtrl,
          decoration: const InputDecoration(
            labelText: 'سبب الرفض',
            border: OutlineInputBorder(),
          ),
          maxLines: 2,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
          AppButton(
            variant: AppButtonVariant.danger,
            label: 'رفض',
            onPressed: () {
              if (reasonCtrl.text.trim().isEmpty) {
                ScaffoldMessenger.of(ctx).showSnackBar(
                  const SnackBar(content: Text('سبب الرفض مطلوب')),
                );
                return;
              }
              Navigator.pop(ctx, reasonCtrl.text);
            },
          ),
        ],
      ),
    );
    if (confirmed == null) return;
    try {
      await _api.post('approval-requests/batch-reject',
          data: {
            'request_ids': _selectedIds.toList(),
            'reason': confirmed,
          });
      _showSuccess('تم رفض ${_selectedIds.length} طلبات');
      _loadAll();
    } catch (e) {
      _showError(ErrorUtils.sanitize(e));
    }
  }

  // ── Detail Dialog ──────────────────────────────────────────────────
  void _showDetail(Map<String, dynamic> req) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('طلب اعتماد #${req['id'] ?? ''}'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _detailRow('نوع الكيان', _entityTypeLabel(req['entity_type'])),
              _detailRow('معرف الكيان', '${req['entity_id'] ?? ''}'),
              _detailRow(
                  'المبلغ', '${formatMoney(req['amount'])} ${req['currency'] ?? ''}'),
              _detailRow('الأولوية', req['priority'] ?? 'normal'),
              _detailRow(
                  'الموعد النهائي', req['due_date'] ?? 'غير محدد'),
              if (req['notes'] != null &&
                  (req['notes'] as String).isNotEmpty)
                _detailRow('ملاحظات', req['notes']),
              if (req['current_step'] != null)
                _detailRow('الخطوة الحالية', '${req['current_step']}'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إغلاق'),
          ),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: AppTextStyles.labelLarge,
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  // ── Helpers ────────────────────────────────────────────────────────
  String _entityTypeLabel(String? type) {
    switch (type) {
      case 'purchase_order':
        return 'أمر شراء';
      case 'invoice':
        return 'فاتورة';
      case 'payment':
        return 'دفعة';
      case 'expense':
        return 'مصروف';
      case 'journal_entry':
        return 'قيد يومية';
      default:
        return type ?? 'غير محدد';
    }
  }

  Color _priorityColor(String? priority) {
    switch (priority) {
      case 'urgent':
        return AppColors.danger;
      case 'high':
        return AppColors.warning;
      case 'normal':
        return AppColors.secondary;
      case 'low':
        return AppColors.textMuted;
      default:
        return AppColors.secondary;
    }
  }

  String _priorityLabel(String? priority) {
    switch (priority) {
      case 'urgent':
        return 'عاجل';
      case 'high':
        return 'مرتفع';
      case 'normal':
        return 'عادي';
      case 'low':
        return 'منخفض';
      default:
        return priority ?? 'عادي';
    }
  }

  // ── Build ──────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_selectionMode
            ? 'تم تحديد ${_selectedIds.length}'
            : 'الاعتمادات'),
        centerTitle: true,
        leading: _selectionMode
            ? IconButton(
                icon: const Icon(Icons.close),
                onPressed: () {
                  setState(() {
                    _selectionMode = false;
                    _selectedIds.clear();
                  });
                },
              )
            : null,
        actions: [
          if (_selectionMode) ...[
            IconButton(
              icon: const Icon(Icons.check_circle, color: AppColors.success),
              tooltip: 'الموافقة على المحدد',
              onPressed: _batchApprove,
            ),
            IconButton(
              icon: const Icon(Icons.cancel, color: AppColors.danger),
              tooltip: 'رفض المحدد',
              onPressed: _batchReject,
            ),
          ] else ...[
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _loadAll,
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
                TextButton(onPressed: _loadAll, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          _buildFilterBar(),
          _buildStatsCards(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: DropdownButtonFormField<String>(
        value: _filterEntityType,
        isDense: true,
        decoration: const InputDecoration(
          labelText: 'تصفية حسب نوع الكيان',
          border: OutlineInputBorder(),
          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ),
        items: [
          const DropdownMenuItem(value: null, child: Text('الكل')),
          ..._entityTypes.map(
            (e) => DropdownMenuItem(value: e, child: Text(_entityTypeLabel(e))),
          ),
        ],
        onChanged: (v) {
          setState(() => _filterEntityType = v);
          _loadAll();
        },
      ),
    );
  }

  Widget _buildStatsCards() {
    if (_stats.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: _buildStatCard(
              'قيد الانتظار',
              '${_stats['pending_count'] ?? _stats['pending'] ?? 0}',
              Icons.hourglass_empty,
              AppColors.warning,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildStatCard(
              'تمت الموافقة',
              '${_stats['approved_count'] ?? _stats['approved'] ?? 0}',
              Icons.check_circle_outline,
              AppColors.success,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildStatCard(
              'مرفوض',
              '${_stats['rejected_count'] ?? _stats['rejected'] ?? 0}',
              Icons.cancel_outlined,
              AppColors.danger,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return AppCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 4),
          Text(value, style: AppTextStyles.statValue.copyWith(color: color)),
          Text(title, style: AppTextStyles.statLabel),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_requests.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.approval, size: 64, color: AppColors.textMuted),
            const SizedBox(height: AppDimens.s3),
            Text(
              'لا توجد طلبات اعتماد معلقة',
              style: AppTextStyles.headlineSmall
                  .copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _loadAll,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        itemCount: _requests.length,
        itemBuilder: (context, index) =>
            _buildRequestCard(_requests[index]),
      ),
    );
  }

  Widget _buildRequestCard(Map<String, dynamic> req) {
    final id = (req['id'] ?? '').toString();
    final entityType = req['entity_type'];
    final amount = parseMoney(req['amount']) ?? Decimal.zero;
    final currency = (req['currency'] ?? '').toString();
    final priority = req['priority'];
    final dueDate = req['due_date'] ?? '';
    final isSelected = _selectedIds.contains(id);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: isSelected ? AppColors.primaryContainer : null,
      child: InkWell(
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
        onTap: () {
          if (_selectionMode) {
            setState(() {
              if (isSelected) {
                _selectedIds.remove(id);
                if (_selectedIds.isEmpty) _selectionMode = false;
              } else {
                _selectedIds.add(id);
              }
            });
          } else {
            _showDetail(req);
          }
        },
        onLongPress: () {
          if (!_selectionMode) {
            setState(() {
              _selectionMode = true;
              _selectedIds.add(id);
            });
          }
        },
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              if (_selectionMode)
                Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: Icon(
                    isSelected ? Icons.check_circle : Icons.radio_button_unchecked,
                    color: isSelected ? AppColors.secondary : AppColors.textMuted,
                  ),
                ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        _buildChip(_entityTypeLabel(entityType), AppColors.secondary),
                        const SizedBox(width: 8),
                        _buildChip(
                          _priorityLabel(priority),
                          _priorityColor(priority),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${formatMoney(amount)} $currency',
                      style: AppTextStyles.moneyMedium,
                    ),
                    const SizedBox(height: 4),
                    if (dueDate.toString().isNotEmpty)
                      Text(
                        'الموعد النهائي: $dueDate',
                        style:
                            TextStyle(fontSize: 12, color: AppColors.textSecondary),
                      ),
                  ],
                ),
              ),
              if (!_selectionMode)
                PopupMenuButton(
                  itemBuilder: (ctx) => [
                    const PopupMenuItem(
                        value: 'approve', child: Text('موافقة')),
                    const PopupMenuItem(
                        value: 'reject',
                        child: Text('رفض', style: TextStyle(color: AppColors.danger))),
                    const PopupMenuItem(
                        value: 'escalate', child: Text('تصعيد')),
                    const PopupMenuItem(
                        value: 'reassign', child: Text('إعادة تعيين')),
                  ],
                  onSelected: (v) {
                    if (v == 'approve') _approveRequest(id);
                    if (v == 'reject') _rejectRequest(id);
                    if (v == 'escalate') _escalateRequest(id);
                    if (v == 'reassign') _reassignRequest(id);
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(
            color: color, fontSize: 11, fontWeight: FontWeight.bold),
      ),
    );
  }
}
