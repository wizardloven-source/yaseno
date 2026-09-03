import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';

class UsersListScreen extends StatefulWidget {
  const UsersListScreen({super.key});

  @override
  State<UsersListScreen> createState() => _UsersListScreenState();
}

class _UsersListScreenState extends State<UsersListScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _users = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadUsers();
  }

  Future<void> _loadUsers() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('auth/users');
      final dynamic items = (response['items'] is List)
          ? response['items']
          : (response is List ? response : const []);
      setState(() {
        _users = (items as List).cast<Map<String, dynamic>>().toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Color _roleColor(String? role) {
    switch (role) {
      case 'admin': return AppColors.danger;
      case 'manager': return AppColors.warning;
      case 'accountant': return AppColors.secondary;
      case 'user': return AppColors.success;
      default: return AppColors.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('المستخدمون'),
        centerTitle: true,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadUsers),
        ],
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(ErrorUtils.sanitize(_error)),
              leading: const Icon(Icons.wifi_off, color: AppColors.warning),
              actions: [
                TextButton(onPressed: _loadUsers, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(child: _buildBody()),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await context.push('/users/create');
          _loadUsers();
        },
        child: const Icon(Icons.person_add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const LoadingState();
    if (_users.isEmpty) {
      return const EmptyState(
        icon: Icons.people_outline,
        title: 'لا يوجد مستخدمون',
      );
    }
    return RefreshIndicator(
      onRefresh: _loadUsers,
      child: ListView.builder(
        padding: const EdgeInsets.all(AppDimens.s3),
        itemCount: _users.length,
        itemBuilder: (context, index) {
          final user = _users[index];
          final role = user['role'] ?? user['role_name'] ?? 'user';
          return Card(
            margin: const EdgeInsets.only(bottom: AppDimens.s2),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppDimens.radiusCard),
            ),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: _roleColor(role).withOpacity(0.1),
                child: Icon(Icons.person, color: _roleColor(role)),
              ),
              title: Text('${user['username'] ?? user['name'] ?? ''}',
                  style: AppTextStyles.titleMedium),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('البريد: ${user['email'] ?? ''}'),
                  Text('الدور: $role'),
                ],
              ),
              trailing: PopupMenuButton(
                itemBuilder: (ctx) => [
                  const PopupMenuItem(value: 'edit', child: Text('تعديل')),
                  const PopupMenuItem(value: 'delete', child: Text('حذف', style: TextStyle(color: AppColors.danger))),
                ],
                onSelected: (v) async {
                  if (v == 'edit') {
                    await context.push('/users/${user['id']}');
                    _loadUsers();
                  } else if (v == 'delete') {
                    _deleteUser(user['id']);
                  }
                },
              ),
              onTap: () async {
                await context.push('/users/${user['id']}');
                _loadUsers();
              },
            ),
          );
        },
      ),
    );
  }

  Future<void> _deleteUser(String userId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف المستخدم'),
        content: const Text('هل أنت متأكد من حذف هذا المستخدم؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          AppButton(label: 'حذف', variant: AppButtonVariant.danger, onPressed: () => Navigator.pop(ctx, true)),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _api.delete('auth/users/$userId');
      _loadUsers();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    }
  }
}
