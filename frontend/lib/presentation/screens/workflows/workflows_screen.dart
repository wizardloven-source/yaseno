import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import 'package:decimal/decimal.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';

class WorkflowsScreen extends StatefulWidget {
  const WorkflowsScreen({super.key});

  @override
  State<WorkflowsScreen> createState() => _WorkflowsScreenState();
}

class _WorkflowsScreenState extends State<WorkflowsScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _workflows = [];
  bool _isLoading = true;
  String? _error;
  String? _filterEntityType;
  String? _filterStatus;

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
    _loadWorkflows();
  }

  Future<void> _loadWorkflows() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final params = <String, dynamic>{};
      if (_filterEntityType != null) params['entity_type'] = _filterEntityType;
      if (_filterStatus != null) params['status'] = _filterStatus;
      final response = await _api.get(
        'workflows',
        queryParameters: params.isNotEmpty ? params : null,
      );
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _workflows = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
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

  // ── Activate / Deactivate ──────────────────────────────────────────
  Future<void> _toggleActivation(Map<String, dynamic> wf) async {
    final isActive = wf['status'] == 'active';
    final endpoint = isActive ? 'deactivate' : 'activate';
    try {
      await _api.post('workflows/${wf['id']}/$endpoint');
      _loadWorkflows();
    } catch (e) {
      _showError(ErrorUtils.sanitize(e));
    }
  }

  // ── Delete ─────────────────────────────────────────────────────────
  Future<void> _deleteWorkflow(Map<String, dynamic> wf) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف سير العمل'),
        content: Text('هل أنت متأكد من حذف "${wf['name']}"؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('حذف', style: TextStyle(color: AppColors.danger)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _api.delete('workflows/${wf['id']}');
      _loadWorkflows();
    } catch (e) {
      _showError(ErrorUtils.sanitize(e));
    }
  }

  // ── Create / Edit Dialog ───────────────────────────────────────────
  Future<void> _showWorkflowDialog({Map<String, dynamic>? existing}) async {
    final isEdit = existing != null;
    final nameCtrl = TextEditingController(text: existing?['name'] ?? '');
    final descCtrl =
        TextEditingController(text: existing?['description'] ?? '');
    String entityType = existing?['entity_type'] ?? _entityTypes.first;
    bool mandatory = existing?['mandatory'] ?? false;
    Decimal autoThreshold =
        parseMoney(existing?['auto_approve_threshold']) ?? Decimal.zero;
    List<Map<String, dynamic>> steps = [];
    if (existing?['steps'] is List) {
      steps = (existing!['steps'] as List)
          .map((s) => Map<String, dynamic>.from(s))
          .toList();
    }

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            title: Text(isEdit ? 'تعديل سير العمل' : 'سير عمل جديد'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'الاسم',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: descCtrl,
                    decoration: const InputDecoration(
                      labelText: 'الوصف',
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 2,
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: entityType,
                    decoration: const InputDecoration(
                      labelText: 'نوع الكيان',
                      border: OutlineInputBorder(),
                    ),
                    items: _entityTypes
                        .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                        .toList(),
                    onChanged: (v) => setDialogState(() => entityType = v!),
                  ),
                  const SizedBox(height: 12),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('إلزامي'),
                    value: mandatory,
                    onChanged: (v) => setDialogState(() => mandatory = v),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    decoration: const InputDecoration(
                      labelText: 'عتبة الموافقة التلقائية',
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.number,
                    onChanged: (v) =>
                        autoThreshold = parseMoney(v) ?? Decimal.zero,
                  ),
                  const SizedBox(height: 12),
                  const Divider(),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('الخطوات',
                          style: AppTextStyles.titleSmall),
                      IconButton(
                        icon: const Icon(Icons.add_circle,
                            color: AppColors.secondary),
                        onPressed: () {
                          setDialogState(() {
                            steps.add({
                              'role': '',
                              'required_approvals': 1,
                              'timeout_hours': 24,
                              'escalation_role': '',
                            });
                          });
                        },
                      ),
                    ],
                  ),
                  ...steps.asMap().entries.map((entry) {
                    final i = entry.key;
                    final step = entry.value;
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(8),
                        child: Column(
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: TextField(
                                    decoration: const InputDecoration(
                                      labelText: 'الدور',
                                      border: OutlineInputBorder(),
                                      isDense: true,
                                    ),
                                    controller:
                                        TextEditingController(text: step['role']),
                                    onChanged: (v) => step['role'] = v,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                IconButton(
                                  icon: const Icon(Icons.remove_circle,
                                      color: AppColors.danger),
                                  onPressed: () {
                                    setDialogState(() => steps.removeAt(i));
                                  },
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Expanded(
                                  child: TextField(
                                    decoration: const InputDecoration(
                                      labelText: 'الموافقات المطلوبة',
                                      border: OutlineInputBorder(),
                                      isDense: true,
                                    ),
                                    keyboardType: TextInputType.number,
                                    controller: TextEditingController(
                                        text:
                                            '${step['required_approvals'] ?? 1}'),
                                    onChanged: (v) =>
                                        step['required_approvals'] =
                                            int.tryParse(v) ?? 1,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: TextField(
                                    decoration: const InputDecoration(
                                      labelText: 'مهلة الساعات',
                                      border: OutlineInputBorder(),
                                      isDense: true,
                                    ),
                                    keyboardType: TextInputType.number,
                                    controller: TextEditingController(
                                        text:
                                            '${step['timeout_hours'] ?? 24}'),
                                    onChanged: (v) =>
                                        step['timeout_hours'] =
                                            int.tryParse(v) ?? 24,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            TextField(
                              decoration: const InputDecoration(
                                labelText: 'دور التصعيد',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              controller: TextEditingController(
                                  text: step['escalation_role'] ?? ''),
                              onChanged: (v) =>
                                  step['escalation_role'] = v,
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('إلغاء'),
              ),
              AppButton(
                variant: AppButtonVariant.success,
                label: isEdit ? 'تحديث' : 'إنشاء',
                onPressed: () async {
                  if (nameCtrl.text.trim().isEmpty) {
                    ScaffoldMessenger.of(ctx).showSnackBar(
                      const SnackBar(content: Text('الاسم مطلوب')),
                    );
                    return;
                  }
                  final payload = {
                    'name': nameCtrl.text.trim(),
                    'description': descCtrl.text.trim(),
                    'entity_type': entityType,
                    'mandatory': mandatory,
                    'auto_approve_threshold': autoThreshold.toString(),
                    'steps': steps,
                  };
                  Navigator.pop(ctx);
                  try {
                    if (isEdit) {
                      await _api.put('workflows/${existing['id']}',
                          data: payload);
                    } else {
                      await _api.post('workflows', data: payload);
                    }
                    _loadWorkflows();
                  } catch (e) {
                    _showError(ErrorUtils.sanitize(e));
                  }
                },
              ),
            ],
          );
        },
      ),
    );
  }

  // ── UI Helpers ─────────────────────────────────────────────────────
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

  Color _statusColor(String? status) {
    return status == 'active' ? AppColors.success : AppColors.secondary;
  }

  String _statusLabel(String? status) {
    return status == 'active' ? 'نشط' : 'غير نشط';
  }

  // ── Build ──────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('سير العمل'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadWorkflows,
          ),
        ],
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadWorkflows, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          _buildFilterBar(),
          Expanded(child: _buildBody()),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showWorkflowDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildFilterBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              value: _filterEntityType,
              isDense: true,
              decoration: const InputDecoration(
                labelText: 'نوع الكيان',
                border: OutlineInputBorder(),
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: [
                const DropdownMenuItem(
                  value: null,
                  child: Text('الكل'),
                ),
                ..._entityTypes.map(
                  (e) => DropdownMenuItem(value: e, child: Text(e)),
                ),
              ],
              onChanged: (v) {
                setState(() => _filterEntityType = v);
                _loadWorkflows();
              },
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: DropdownButtonFormField<String>(
              value: _filterStatus,
              isDense: true,
              decoration: const InputDecoration(
                labelText: 'الحالة',
                border: OutlineInputBorder(),
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: const [
                DropdownMenuItem(value: null, child: Text('الكل')),
                DropdownMenuItem(value: 'active', child: Text('نشط')),
                DropdownMenuItem(value: 'inactive', child: Text('غير نشط')),
              ],
              onChanged: (v) {
                setState(() => _filterStatus = v);
                _loadWorkflows();
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const LoadingState();
    }
    if (_workflows.isEmpty) {
      return const EmptyState(
        icon: Icons.account_tree_outlined,
        title: 'لا توجد سير عمل',
      );
    }
    return RefreshIndicator(
      onRefresh: _loadWorkflows,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        itemCount: _workflows.length,
        itemBuilder: (context, index) => _buildWorkflowCard(_workflows[index]),
      ),
    );
  }

  Widget _buildWorkflowCard(Map<String, dynamic> wf) {
    final name = wf['name'] ?? '';
    final entityType = wf['entity_type'];
    final status = wf['status'];
    final stepsCount = (wf['steps'] is List) ? (wf['steps'] as List).length : 0;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          backgroundColor: _statusColor(status).withOpacity(0.1),
          child: Icon(
            Icons.account_tree,
            color: _statusColor(status),
          ),
        ),
        title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Row(
              children: [
                _buildChip(_entityTypeLabel(entityType), AppColors.secondary),
                const SizedBox(width: 8),
                _buildChip(_statusLabel(status), _statusColor(status)),
                const SizedBox(width: 8),
                _buildChip('$stepsCount خطوات', AppColors.warning),
              ],
            ),
          ],
        ),
        trailing: PopupMenuButton(
          itemBuilder: (ctx) => [
            const PopupMenuItem(value: 'edit', child: Text('تعديل')),
            PopupMenuItem(
              value: 'toggle',
              child: Text(
                status == 'active' ? 'تعطيل' : 'تفعيل',
              ),
            ),
            const PopupMenuItem(
              value: 'delete',
              child: Text('حذف', style: TextStyle(color: AppColors.danger)),
            ),
          ],
          onSelected: (v) {
            if (v == 'edit') {
              _showWorkflowDialog(existing: wf);
            } else if (v == 'toggle') {
              _toggleActivation(wf);
            } else if (v == 'delete') {
              _deleteWorkflow(wf);
            }
          },
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
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold),
      ),
    );
  }
}
