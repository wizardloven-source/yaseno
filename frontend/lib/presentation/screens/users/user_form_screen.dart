import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';

class UserFormScreen extends StatefulWidget {
  final String? userId;

  const UserFormScreen({super.key, this.userId});

  @override
  State<UserFormScreen> createState() => _UserFormScreenState();
}

class _UserFormScreenState extends State<UserFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  String _role = 'user';
  bool _isActive = true;
  bool _isSaving = false;
  bool _isLoadingEdit = false;
  bool _obscurePassword = true;

  bool get _isEdit => widget.userId != null;

  @override
  void initState() {
    super.initState();
    if (_isEdit) _loadUser();
  }

  Future<void> _loadUser() async {
    setState(() => _isLoadingEdit = true);
    try {
      final response = await ApiService().get('auth/users/${widget.userId}');
      final data = response['data'] ?? response;
      _usernameController.text = data['username'] ?? '';
      _emailController.text = data['email'] ?? '';
      _firstNameController.text = data['first_name'] ?? '';
      _lastNameController.text = data['last_name'] ?? '';
      _role = data['role'] ?? data['role_name'] ?? 'user';
      _isActive = data['is_active'] ?? true;
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    } finally {
      if (mounted) setState(() => _isLoadingEdit = false);
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSaving = true);
    try {
      final api = ApiService();
      final body = {
        'username': _usernameController.text.trim(),
        'email': _emailController.text.trim(),
        'first_name': _firstNameController.text.trim(),
        'last_name': _lastNameController.text.trim(),
        'role': _role,
        'is_active': _isActive,
      };
      if (_passwordController.text.isNotEmpty) {
        body['password'] = _passwordController.text;
      }
      if (_isEdit) {
        await api.put('auth/users/${widget.userId}', data: body);
      } else {
        await api.post('auth/users', data: body);
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _firstNameController.dispose();
    _lastNameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_isEdit ? 'تعديل المستخدم' : 'مستخدم جديد')),
      body: _isLoadingEdit
          ? const LoadingState(skeleton: false)
          : Padding(
              padding: const EdgeInsets.all(AppDimens.s3),
              child: Form(
                key: _formKey,
                child: ListView(
                  children: [
                    TextFormField(
                      controller: _usernameController,
                      decoration: const InputDecoration(labelText: 'اسم المستخدم', border: OutlineInputBorder()),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'مطلوب' : null,
                    ),
                    const SizedBox(height: AppDimens.s3),
                    TextFormField(
                      controller: _emailController,
                      decoration: const InputDecoration(labelText: 'البريد الإلكتروني', border: OutlineInputBorder()),
                      keyboardType: TextInputType.emailAddress,
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'مطلوب' : null,
                    ),
                    const SizedBox(height: AppDimens.s3),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _firstNameController,
                            decoration: const InputDecoration(labelText: 'الاسم الأول', border: OutlineInputBorder()),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _lastNameController,
                            decoration: const InputDecoration(labelText: 'اسم العائلة', border: OutlineInputBorder()),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppDimens.s3),
                    DropdownButtonFormField<String>(
                      value: _role,
                      decoration: const InputDecoration(labelText: 'الدور', border: OutlineInputBorder()),
                      items: const [
                        DropdownMenuItem(value: 'user', child: Text('مستخدم')),
                        DropdownMenuItem(value: 'accountant', child: Text('محاسب')),
                        DropdownMenuItem(value: 'manager', child: Text('مدير')),
                        DropdownMenuItem(value: 'admin', child: Text('مدير النظام')),
                      ],
                      onChanged: (v) => setState(() => _role = v!),
                    ),
                    const SizedBox(height: AppDimens.s3),
                    SwitchListTile(
                      title: const Text('نشط'),
                      value: _isActive,
                      activeColor: AppColors.success,
                      onChanged: (v) => setState(() => _isActive = v),
                    ),
                    const SizedBox(height: AppDimens.s3),
                    TextFormField(
                      controller: _passwordController,
                      decoration: InputDecoration(
                        labelText: _isEdit ? 'كلمة المرور (اتركها فارغة لعدم التغيير)' : 'كلمة المرور',
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(_obscurePassword ? Icons.visibility : Icons.visibility_off),
                          onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                        ),
                      ),
                      obscureText: _obscurePassword,
                      validator: (v) {
                        if (!_isEdit && (v == null || v.isEmpty)) return 'مطلوب';
                        return null;
                      },
                    ),
                    const SizedBox(height: AppDimens.s4),
                    AppButton(
                      label: _isEdit ? 'تحديث' : 'إنشاء',
                      icon: Icons.save,
                      variant: AppButtonVariant.success,
                      loading: _isSaving,
                      expanded: true,
                      onPressed: _save,
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
