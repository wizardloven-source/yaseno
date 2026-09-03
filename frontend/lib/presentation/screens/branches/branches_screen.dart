import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../presentation/widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';

class BranchesScreen extends StatefulWidget {
  const BranchesScreen({super.key});

  @override
  State<BranchesScreen> createState() => _BranchesScreenState();
}

class _BranchesScreenState extends State<BranchesScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _branches = [];
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
      final response = await _api.get('branches');
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _branches = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() { _error = ErrorUtils.sanitize(e); _isLoading = false; });
    }
  }

  Future<void> _createBranch() async {
    final codeCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    final customerCtrl = TextEditingController();
    final cityCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('إضافة فرع جديد'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: codeCtrl, decoration: const InputDecoration(labelText: 'الرمز *', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'اسم الفرع *', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: customerCtrl, decoration: const InputDecoration(labelText: 'اسم العميل *', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: cityCtrl, decoration: const InputDecoration(labelText: 'المدينة', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: phoneCtrl, decoration: const InputDecoration(labelText: 'الهاتف', border: OutlineInputBorder())),
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
              child: const Text('إلغاء')),
          AppButton(
            label: 'حفظ',
            variant: AppButtonVariant.success,
            onPressed: () {
              if (codeCtrl.text.isEmpty || nameCtrl.text.isEmpty || customerCtrl.text.isEmpty) {
                ScaffoldMessenger.of(ctx).showSnackBar(const SnackBar(content: Text('يرجى ملء الحقول المطلوبة')));
                return;
              }
              Navigator.pop(ctx, true);
            },
          ),
        ],
      ),
    );
    if (result != true) {
      codeCtrl.dispose();
      nameCtrl.dispose();
      customerCtrl.dispose();
      cityCtrl.dispose();
      phoneCtrl.dispose();
      return;
    }
    try {
      await _api.post('branches', data: {
        'code': codeCtrl.text.trim(),
        'name': nameCtrl.text.trim(),
        'customer_name': customerCtrl.text.trim(),
        'city': cityCtrl.text.trim(),
        'phone': phoneCtrl.text.trim(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم إنشاء الفرع بنجاح'), backgroundColor: AppColors.success));
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
    codeCtrl.dispose();
    nameCtrl.dispose();
    customerCtrl.dispose();
    cityCtrl.dispose();
    phoneCtrl.dispose();
  }

  Future<void> _toggleBranch(String id, bool isActive) async {
    try {
      final endpoint = isActive ? 'branches/$id/deactivate' : 'branches/$id/activate';
      await _api.post(endpoint);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(isActive ? 'تم تعطيل الفرع' : 'تفعيل الفرع بنجاح'), backgroundColor: AppColors.success),
        );
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  Future<void> _deleteBranch(String id) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف الفرع'),
        content: const Text('هل أنت متأكد من حذف هذا الفرع؟'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
              child: const Text('إلغاء')),
          AppButton(
            label: 'حذف',
            variant: AppButtonVariant.danger,
            onPressed: () => Navigator.pop(ctx, true),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _api.delete('branches/$id');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم حذف الفرع'), backgroundColor: AppColors.success));
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  Future<void> _editBranch(Map<String, dynamic> branch) async {
    final codeCtrl = TextEditingController(text: branch['code'] ?? '');
    final nameCtrl = TextEditingController(text: branch['name'] ?? '');
    final customerCtrl = TextEditingController(text: branch['customer_name'] ?? branch['customer'] ?? '');
    final cityCtrl = TextEditingController(text: branch['city'] ?? '');
    final phoneCtrl = TextEditingController(text: branch['phone'] ?? '');
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تعديل الفرع'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: codeCtrl, decoration: const InputDecoration(labelText: 'الرمز *', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'اسم الفرع *', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: customerCtrl, decoration: const InputDecoration(labelText: 'اسم العميل *', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: cityCtrl, decoration: const InputDecoration(labelText: 'المدينة', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: phoneCtrl, decoration: const InputDecoration(labelText: 'الهاتف', border: OutlineInputBorder())),
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              style: TextButton.styleFrom(foregroundColor: AppColors.buttonCancel),
              child: const Text('إلغاء')),
          AppButton(
            label: 'حفظ',
            variant: AppButtonVariant.success,
            onPressed: () {
              if (codeCtrl.text.isEmpty || nameCtrl.text.isEmpty || customerCtrl.text.isEmpty) {
                ScaffoldMessenger.of(ctx).showSnackBar(const SnackBar(content: Text('يرجى ملء الحقول المطلوبة')));
                return;
              }
              Navigator.pop(ctx, true);
            },
          ),
        ],
      ),
    );
    if (result != true) return;
    try {
      await _api.put('branches/${branch['id']}', data: {
        'code': codeCtrl.text.trim(),
        'name': nameCtrl.text.trim(),
        'customer_name': customerCtrl.text.trim(),
        'city': cityCtrl.text.trim(),
        'phone': phoneCtrl.text.trim(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم تعديل الفرع بنجاح'), backgroundColor: AppColors.success));
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  String _branchTypeLabel(String? type) {
    switch (type) {
      case 'warehouse': return 'مستودع';
      case 'branch': return 'فرع';
      case 'office': return 'مكتب';
      default: return type ?? 'غير محدد';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('فروع العملاء'),
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
        onPressed: _createBranch,
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const LoadingState();
    if (_branches.isEmpty)
      return const EmptyState(
        icon: Icons.store,
        title: 'لا توجد فروع',
      );
    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: _branches.length,
      itemBuilder: (context, index) {
        final b = _branches[index];
        final bool isActive = (b['status'] ?? 'active').toString() == 'active';
        return Card(
          margin: const EdgeInsets.symmetric(vertical: 4),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: isActive ? AppColors.successContainer : AppColors.surfaceVariant,
              child: Icon(Icons.store, color: isActive ? AppColors.success : AppColors.textSecondary, size: 20),
            ),
            title: Text(b['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text(
              '${b['code'] ?? ''} - ${b['city'] ?? ''} ${b['phone'] != null ? '| ${b['phone']}' : ''}',
              style: const TextStyle(fontSize: 12),
            ),
              trailing: PopupMenuButton<String>(
              onSelected: (value) {
                if (value == 'activate') _toggleBranch(b['id'].toString(), isActive);
                if (value == 'delete') _deleteBranch(b['id'].toString());
              },
              itemBuilder: (ctx) => [
                PopupMenuItem(value: 'activate', child: Text(isActive ? 'تعطيل' : 'تفعيل')),
                const PopupMenuItem(value: 'delete', child: Text('حذف', style: TextStyle(color: AppColors.danger))),
              ],
            ),
            onTap: () => _editBranch(b),
          ),
        );
      },
    );
  }
}
