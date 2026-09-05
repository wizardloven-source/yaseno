import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../../theme/app_colors.dart';
import '../../../presentation/widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';

class CentersScreen extends StatefulWidget {
  const CentersScreen({super.key});

  @override
  State<CentersScreen> createState() => _CentersScreenState();
}

class _CentersScreenState extends State<CentersScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _centers = [];
  bool _isLoading = true;
  String? _error;

  final _codeController = TextEditingController();
  final _nameController = TextEditingController();
  final _parentCodeController = TextEditingController();
  final _managerController = TextEditingController();
  final _budgetController = TextEditingController();
  String _selectedType = 'department';
  String _selectedStatus = 'active';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _codeController.dispose();
    _nameController.dispose();
    _parentCodeController.dispose();
    _managerController.dispose();
    _budgetController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('centers');
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _centers = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'department':
        return 'قسم';
      case 'project':
        return 'مشروع';
      case 'cost_center':
        return 'مركز تكلفة';
      default:
        return type;
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'active':
        return 'نشط';
      case 'suspended':
        return 'معلّق';
      case 'closed':
        return 'مغلق';
      default:
        return status;
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'active':
        return AppColors.success;
      case 'suspended':
        return AppColors.warning;
      case 'closed':
        return AppColors.danger;
      default:
        return AppColors.textSecondary;
    }
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'active':
        return Icons.check_circle;
      case 'suspended':
        return Icons.pause_circle;
      case 'closed':
        return Icons.cancel;
      default:
        return Icons.help_outline;
    }
  }

  Map<String, dynamic> _buildTree(List<Map<String, dynamic>> centers) {
    final map = <String, Map<String, dynamic>>{};
    for (final c in centers) {
      final id = c['id']?.toString() ?? '';
      map[id] = {...c, 'children': <Map<String, dynamic>>[]};
    }

    final roots = <Map<String, dynamic>>[];
    for (final c in centers) {
      final id = c['id']?.toString() ?? '';
      final parentId = c['parent_id']?.toString() ??
          c['parent_code']?.toString() ??
          '';
      if (parentId.isNotEmpty && map.containsKey(parentId)) {
        map[parentId]!['children'].add(map[id]!);
      } else {
        roots.add(map[id]!);
      }
    }
    return {'roots': roots, 'map': map};
  }

  void _showCenterDialog({Map<String, dynamic>? center}) {
    final isEdit = center != null;
    _codeController.text = center?['code'] ?? '';
    _nameController.text = center?['name'] ?? '';
    _parentCodeController.text =
        center?['parent_code']?.toString() ?? '';
    _managerController.text = center?['manager_name'] ?? '';
    _budgetController.text = (center?['budget_total'] ?? '').toString();
    _selectedType = center?['center_type'] ?? center?['type'] ?? 'department';
    _selectedStatus = center?['status'] ?? 'active';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(isEdit ? 'تعديل المركز' : 'إضافة مركز تكلفة'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!isEdit)
                TextField(
                  controller: _codeController,
                  decoration: const InputDecoration(
                    labelText: 'الرمز',
                    hintText: 'مثال: CC-001',
                  ),
                ),
              const SizedBox(height: 12),
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'الاسم',
                  hintText: 'مثال: قسم المحاسبة',
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _selectedType,
                decoration: const InputDecoration(labelText: 'النوع'),
                items: const [
                  DropdownMenuItem(
                      value: 'department', child: Text('قسم')),
                  DropdownMenuItem(value: 'project', child: Text('مشروع')),
                  DropdownMenuItem(
                      value: 'cost_center', child: Text('مركز تكلفة')),
                ],
                onChanged: (v) {
                  if (v != null) _selectedType = v;
                },
              ),
              const SizedBox(height: 12),
              Autocomplete<String>(
                initialValue: TextEditingValue(
                    text: _parentCodeController.text,
                    selection: TextSelection.collapsed(
                        offset: _parentCodeController.text.length)),
                optionsBuilder: (value) {
                  if (value.text.isEmpty) return const Iterable<String>.empty();
                  final codes = _centers
                      .map((c) => c['code']?.toString() ?? '')
                      .toList();
                  return codes.where((c) => c
                      .toLowerCase()
                      .contains(value.text.toLowerCase()));
                },
                onSelected: (v) {
                  _parentCodeController.text = v;
                },
                fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
                  return TextField(
                    controller: controller,
                    focusNode: focusNode,
                    decoration: const InputDecoration(
                      labelText: 'المركز الأب (قدم رمزاً)',
                      hintText: 'اتركه فارغًا إذا كان في الأعلى',
                    ),
                  );
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _managerController,
                decoration: const InputDecoration(labelText: 'اسم المدير'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _budgetController,
                decoration: const InputDecoration(labelText: 'الميزانية'),
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
              ),
            ],
          ),
        ),
        actions: [
TextButton(
              onPressed: () => Navigator.pop(ctx),
              style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
              child: const Text('إلغاء'),
            ),
            AppButton(
              label: 'حفظ',
              variant: AppButtonVariant.success,
              onPressed: () => _saveCenter(ctx, center),
            ),
        ],
      ),
    );
  }

  Future<void> _saveCenter(
      BuildContext dialogContext, Map<String, dynamic>? center) async {
    final id = center?['id'];
    final data = {
      'name': _nameController.text.trim(),
      'center_type': _selectedType,
      'parent_code': _parentCodeController.text.trim().isEmpty
          ? null
          : _parentCodeController.text.trim(),
      'manager_name': _managerController.text.trim().isEmpty
          ? null
          : _managerController.text.trim(),
      'budget_amount': double.tryParse(_budgetController.text),
      'budget_currency': center?['budget_currency'] ?? CurrencyHelper.baseCurrency,
    };

    if ((data['name'] ?? '').toString().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('الاسم مطلوب')),
      );
      return;
    }

    try {
      if (id != null) {
        data['version'] = center?['version'] ?? 1;
        await _api.put('centers/$id', data: data);
      } else {
        data['code'] = _codeController.text.trim();
        if ((data['code'] ?? '').toString().isEmpty) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('الرمز مطلوب')),
          );
          return;
        }
        await _api.post('centers', data: data);
      }
      Navigator.pop(dialogContext);
      _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Future<void> _deleteCenter(String id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف المركز'),
        content: const Text('هل أنت متأكد من حذف هذا المركز؟'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
              child: const Text('إلغاء')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('حذف', style: TextStyle(color: AppColors.danger))),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _api.delete('centers/$id');
      _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Future<void> _changeStatus(String id, String action) async {
    try {
      await _api.post('centers/$id/$action');
      _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  void _showSummary(Map<String, dynamic> center) async {
    final code = center['code']?.toString() ?? '';
    if (code.isEmpty) return;
    DateTime? from = DateTime(DateTime.now().year, 1, 1);
    DateTime to = DateTime.now();
    try {
      final response = await _api.get('centers/$code/summary',
          queryParameters: {
            'from_date': from.toIso8601String().split('T')[0],
            'to_date': to.toIso8601String().split('T')[0],
          });
      final data = response['data'] ?? {};
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) {
            final totalAllocated = data['total_allocated'];
            final count = data['allocations_count'];
            final utilization = data['budget_utilization'];
            final over = data['is_over_budget'] == true;
            final c = data['center'] is Map
                ? data['center'] as Map
                : null;
            return AlertDialog(
              title: Text('ملخص ${center['name'] ?? ''}'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _summaryRow('الرمز', '${center['code'] ?? ''}'),
                  if (c != null) ...[
                    _summaryRow('النوع', _typeLabel('${c['center_type'] ?? ''}')),
                    _summaryRow('الحالة', _statusLabel('${c['status'] ?? ''}')),
                  ],
                  _summaryRow('إجمالي المخصص', _fmt(totalAllocated)),
                  _summaryRow('عدد التوزيعات', '$count'),
                  _summaryRow('نسبة الاستخدام من الميزانية', _fmt(utilization)),
                  _summaryRow('تجاوز الميزانية', over ? 'نعم' : 'لا'),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
                  child: const Text('إغلاق'),
                ),
              ],
            );
          },
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Widget _summaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  String _fmt(dynamic value) {
    if (value == null) return '0';
    try {
      final n = double.parse(value.toString());
      return n.toStringAsFixed(2);
    } catch (_) {
      return value.toString();
    }
  }

  void _showAllocationDialog() {
    String sourceCode = '';
    final targetCodes = <String>[];
    final amountController = TextEditingController();
    DateTime periodStart = DateTime(DateTime.now().year, 1, 1);
    DateTime periodEnd = DateTime.now();
    String method = 'equal';
    final descriptionController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          final centerCodes = _centers
              .map((c) => c['code']?.toString() ?? '')
              .where((c) => c.isNotEmpty)
              .toList();

          Widget codeMultiSelect(String label, List<String> selected) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(color: AppColors.textSecondary)),
                Wrap(
                  spacing: 6,
                  children: centerCodes
                      .map((code) => FilterChip(
                            label: Text(code),
                            selected: selected.contains(code),
                            onSelected: (sel) {
                              setDialogState(() {
                                if (sel) {
                                  if (!selected.contains(code)) {
                                    selected.add(code);
                                  }
                                } else {
                                  selected.remove(code);
                                }
                              });
                            },
                          ))
                      .toList(),
                ),
              ],
            );
          }

          return AlertDialog(
            title: const Text('توزيع التكلفة بين المراكز'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: sourceCode.isEmpty ? null : sourceCode,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'مركز المصدر'),
                    items: centerCodes
                        .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                        .toList(),
                    onChanged: (v) {
                      setDialogState(() {
                        if (v != null) sourceCode = v;
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: amountController,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'المبلغ',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  codeMultiSelect('مراكز الهدف', targetCodes),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    initialValue: method,
                    decoration: const InputDecoration(labelText: 'طريقة التوزيع'),
                    items: const [
                      DropdownMenuItem(value: 'equal', child: Text('بالتساوي')),
                      DropdownMenuItem(
                          value: 'percentage', child: Text('بالنسبة')),
                      DropdownMenuItem(
                          value: 'fixed', child: Text('مبلغ ثابت')),
                    ],
                    onChanged: (v) {
                      setDialogState(() {
                        if (v != null) method = v;
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () async {
                            final picked = await showDatePicker(
                              context: ctx,
                              initialDate: periodStart,
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2030),
                            );
                            if (picked != null) {
                              setDialogState(() => periodStart = picked);
                            }
                          },
                          icon: const Icon(Icons.calendar_today, size: 16),
                          label: Text(
                              'من: ${periodStart.toIso8601String().split('T')[0]}'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () async {
                            final picked = await showDatePicker(
                              context: ctx,
                              initialDate: periodEnd,
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2030),
                            );
                            if (picked != null) {
                              setDialogState(() => periodEnd = picked);
                            }
                          },
                          icon: const Icon(Icons.calendar_today, size: 16),
                          label: Text(
                              'إلى: ${periodEnd.toIso8601String().split('T')[0]}'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: descriptionController,
                    decoration: const InputDecoration(
                      labelText: 'الوصف',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
                child: const Text('إلغاء'),
              ),
              AppButton(
                label: 'حفظ التوزيع',
                variant: AppButtonVariant.success,
                onPressed: () async {
                  final amount = double.tryParse(amountController.text.trim());
                  if (sourceCode.isEmpty) {
                    _snack('اختر مركز المصدر');
                    return;
                  }
                  if (targetCodes.isEmpty) {
                    _snack('اختر مركز هدف واحد على الأقل');
                    return;
                  }
                  if (amount == null || amount <= 0) {
                    _snack('أدخل مبلغاً صحيحاً');
                    return;
                  }
                  try {
                    await _api.post('centers/allocations', data: {
                      'source_center_code': sourceCode,
                      'target_center_codes': targetCodes,
                      'amount': amount,
                      'period_start':
                          periodStart.toIso8601String().split('T')[0],
                      'period_end': periodEnd.toIso8601String().split('T')[0],
                      'method': method,
                      'description': descriptionController.text.trim().isEmpty
                          ? null
                          : descriptionController.text.trim(),
                    });
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('تم إنشاء التوزيع بنجاح'),
                          backgroundColor: AppColors.success,
                        ),
                      );
                    }
                    Navigator.pop(ctx);
                  } catch (e) {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                            content: Text(ErrorUtils.sanitize(e)),
                            backgroundColor: AppColors.danger),
                      );
                    }
                  }
                },
              ),
            ],
          );
        },
      ),
    );
    amountController.dispose();
    descriptionController.dispose();
  }

  void _snack(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: AppColors.danger),
    );
  }

  Widget _buildCenterTile(Map<String, dynamic> center, {int depth = 0}) {
    final status = center['status'] ?? 'active';
    final children =
        (center['children'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    final hasChildren = children.isNotEmpty;

    final tile = Card(
      margin: const EdgeInsets.only(bottom: 4),
      child: ListTile(
        contentPadding: EdgeInsets.only(left: 16, right: 16, top: 4, bottom: 4),
        leading: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (depth > 0)
              Padding(
                padding: EdgeInsets.only(right: (depth * 16.0)),
                child: Icon(Icons.subdirectory_arrow_right,
                    size: 20, color: Colors.grey[400]),
              ),
            Icon(_statusIcon(status), color: _statusColor(status), size: 28),
          ],
        ),
        title: Text('${center['name'] ?? ''}',
            style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('الرمز: ${center['code'] ?? ''}'),
            Text(
                'النوع: ${_typeLabel(center['center_type'] ?? center['type'] ?? '')}'),
            Text('الحالة: ${_statusLabel(status)}'),
            if (center['manager_name'] != null &&
                (center['manager_name'] as String).isNotEmpty)
              Text('المدير: ${center['manager_name']}'),
            if (center['budget_total'] != null)
              Text(
                  'الميزانية: ${_fmt(center['budget_total'])} ${center['budget_currency'] ?? ''}'),
          ],
        ),
        trailing: PopupMenuButton(
          itemBuilder: (ctx) => [
            const PopupMenuItem(value: 'edit', child: Text('تعديل')),
            const PopupMenuItem(value: 'summary', child: Text('الملخص')),
            if (status != 'active')
              const PopupMenuItem(
                  value: 'activate', child: Text('تفعيل')),
            if (status == 'active')
              const PopupMenuItem(
                  value: 'suspend', child: Text('تعليق')),
            if (status != 'closed')
              const PopupMenuItem(
                  value: 'close', child: Text('إغلاق')),
            const PopupMenuItem(
                value: 'delete',
                child:
                    Text('حذف', style: TextStyle(color: AppColors.danger))),
          ],
          onSelected: (v) {
            if (v == 'edit') {
              _showCenterDialog(center: center);
            } else if (v == 'summary') {
              _showSummary(center);
            } else if (v == 'activate') {
              _changeStatus(center['id'], 'activate');
            } else if (v == 'suspend') {
              _changeStatus(center['id'], 'suspend');
            } else if (v == 'close') {
              _changeStatus(center['id'], 'close');
            } else if (v == 'delete') {
              _deleteCenter(center['id']);
            }
          },
        ),
      ),
    );

    if (!hasChildren) return tile;

    return Column(
      children: [
        tile,
        ...children
            .map((child) => _buildCenterTile(child, depth: depth + 1)),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('مراكز التكلفة'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.call_split, color: AppColors.success),
            tooltip: 'توزيع التكلفة',
            onPressed: _showAllocationDialog,
          ),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
        ],
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadData, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(child: _buildBody()),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCenterDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const LoadingState();
    if (_centers.isEmpty) {
      return const EmptyState(
        icon: Icons.account_tree,
        title: 'لا توجد مراكز تكلفة',
      );
    }

    final tree = _buildTree(_centers);
    final roots = tree['roots'] as List<Map<String, dynamic>>;

    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: roots
            .map((center) => _buildCenterTile(center))
            .toList(),
      ),
    );
  }
}
