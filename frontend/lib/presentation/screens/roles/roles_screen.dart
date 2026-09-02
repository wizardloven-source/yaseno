import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';

class RolesScreen extends StatefulWidget {
  const RolesScreen({super.key});

  @override
  State<RolesScreen> createState() => _RolesScreenState();
}

class _RolesScreenState extends State<RolesScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _roles = [];
  List<Map<String, dynamic>> _permissions = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final rolesRes = await _api.get('roles');
      final permsRes = await _api.get('permissions');
      final dynamic rolesItems = (rolesRes['items'] is List)
          ? rolesRes['items']
          : (rolesRes is List ? rolesRes : const []);
      final dynamic permsItems = (permsRes['items'] is List)
          ? permsRes['items']
          : (permsRes is List ? permsRes : const []);
      setState(() {
        _roles = (rolesItems as List).cast<Map<String, dynamic>>().toList();
        _permissions = (permsItems as List).cast<Map<String, dynamic>>().toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() { _error = ErrorUtils.sanitize(e); _isLoading = false; });
    }
  }

  Future<void> _showRoleDialog({Map<String, dynamic>? existing}) async {
    final isEdit = existing != null;
    final nameCtrl = TextEditingController(text: existing?['name'] ?? '');
    final displayNameCtrl = TextEditingController(text: existing?['display_name'] ?? '');
    final descCtrl = TextEditingController(text: existing?['description'] ?? '');
    bool isAdmin = existing?['is_admin'] ?? false;
    List<String> selectedPermIds = (existing?['permissions'] as List?)
        ?.map((p) => p['id'].toString()).toList() ?? [];

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Text(isEdit ? 'تعديل الدور' : 'إضافة دور جديد'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(labelText: 'الاسم *', border: OutlineInputBorder()),
                  enabled: !isEdit,
                ),
                const SizedBox(height: 12),
                TextField(controller: displayNameCtrl, decoration: const InputDecoration(labelText: 'الاسم المعروض', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                TextField(controller: descCtrl, decoration: const InputDecoration(labelText: 'الوصف', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                SwitchListTile(
                  title: const Text('مدير النظام'),
                  value: isAdmin,
                  onChanged: (v) => setDialogState(() => isAdmin = v),
                  contentPadding: EdgeInsets.zero,
                ),
                const SizedBox(height: 8),
                const Text('الصلاحيات:', style: AppTextStyles.labelLarge),
                const SizedBox(height: 8),
                SizedBox(
                  height: 250,
                  width: 350,
                  child: ListView.builder(
                    itemCount: _permissions.length,
                    itemBuilder: (ctx, i) {
                      final p = _permissions[i];
                      final selected = selectedPermIds.contains(p['id']);
                      return CheckboxListTile(
                        dense: true,
                        title: Text(p['name'] ?? p['code'] ?? '', style: const TextStyle(fontSize: 12)),
                        subtitle: Text('${p['category'] ?? ''} - ${p['code'] ?? ''}', style: const TextStyle(fontSize: 10)),
                        value: selected,
                        onChanged: (v) {
                          setDialogState(() {
                            if (v == true) {
                              selectedPermIds.add(p['id']);
                            } else {
                              selectedPermIds.remove(p['id']);
                            }
                          });
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
            AppButton(
              label: 'حفظ',
              variant: AppButtonVariant.success,
              onPressed: () {
                if (nameCtrl.text.isEmpty) {
                  ScaffoldMessenger.of(ctx).showSnackBar(const SnackBar(content: Text('الاسم مطلوب')));
                  return;
                }
                Navigator.pop(ctx, true);
              },
            ),
          ],
        ),
      ),
    );

    if (result != true) return;
    try {
      if (isEdit) {
        await _api.put('roles/${existing!['id']}', data: {
          'display_name': displayNameCtrl.text.trim(),
          'description': descCtrl.text.trim(),
          'is_admin': isAdmin,
          'permission_ids': selectedPermIds,
        });
      } else {
        await _api.post('roles', data: {
          'name': nameCtrl.text.trim(),
          'display_name': displayNameCtrl.text.trim(),
          'description': descCtrl.text.trim(),
          'is_admin': isAdmin,
          'permission_ids': selectedPermIds,
        });
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(isEdit ? 'تم تحديث الدور' : 'تم إنشاء الدور'), backgroundColor: AppColors.success),
        );
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  Future<void> _deleteRole(Map<String, dynamic> role) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف الدور'),
        content: Text('هل أنت متأكد من حذف الدور "${role['name']}"؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          AppButton(label: 'حذف', variant: AppButtonVariant.danger, onPressed: () => Navigator.pop(ctx, true)),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _api.delete('roles/${role['id']}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم حذف الدور'), backgroundColor: AppColors.success));
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الأدوار والصلاحيات'),
        centerTitle: true,
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData)],
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
        onPressed: () => _showRoleDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_roles.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.security, size: 64, color: AppColors.textHint),
            SizedBox(height: 16),
            Text('لا توجد أدوار مسجلة', style: TextStyle(fontSize: 16, color: AppColors.textSecondary)),
          ],
        ),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(AppDimens.s2),
      itemCount: _roles.length,
      itemBuilder: (context, index) {
        final role = _roles[index];
        final perms = (role['permissions'] as List?) ?? [];
        return Card(
          margin: const EdgeInsets.symmetric(vertical: AppDimens.s1),
          child: ExpansionTile(
            leading: CircleAvatar(
              backgroundColor: (role['is_admin'] == true) ? AppColors.warning.withOpacity(0.15) : AppColors.secondary.withOpacity(0.15),
              child: Icon(
                role['is_admin'] == true ? Icons.admin_panel_settings : Icons.security,
                color: role['is_admin'] == true ? AppColors.warning : AppColors.secondary,
                size: 20,
              ),
            ),
            title: Text(role['display_name'] ?? role['name'] ?? '', style: AppTextStyles.titleMedium),
            subtitle: Text('${role['name']} | ${perms.length} صلاحية', style: AppTextStyles.labelMedium),
            trailing: PopupMenuButton<String>(
              onSelected: (v) {
                if (v == 'edit') _showRoleDialog(existing: role);
                if (v == 'delete') _deleteRole(role);
              },
              itemBuilder: (ctx) => [
                const PopupMenuItem(value: 'edit', child: Text('تعديل')),
                const PopupMenuItem(value: 'delete', child: Text('حذف', style: TextStyle(color: AppColors.danger))),
              ],
            ),
            children: perms.isEmpty
                ? [const Padding(padding: EdgeInsets.all(AppDimens.s3), child: Text('لا توجد صلاحيات', style: TextStyle(color: AppColors.textSecondary)))]
                : perms.map<Widget>((p) => ListTile(
                    dense: true,
                    leading: const Icon(Icons.check_circle_outline, size: 16, color: AppColors.success),
                    title: Text(p['name'] ?? '', style: const TextStyle(fontSize: 13)),
                    subtitle: Text(p['code'] ?? '', style: const TextStyle(fontSize: 11, color: AppColors.textHint)),
                    trailing: Text(p['category'] ?? '', style: const TextStyle(fontSize: 10, color: AppColors.textHint)),
                  )).toList(),
          ),
        );
      },
    );
  }
}
