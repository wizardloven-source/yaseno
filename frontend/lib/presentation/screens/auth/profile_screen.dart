import 'package:flutter/material.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../widgets/app_widgets.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ApiService _api = ApiService();
  final _oldPasswordController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _passwordFormKey = GlobalKey<FormState>();
  Map<String, dynamic>? _userInfo;
  bool _isLoading = true;
  bool _isChangingPassword = false;
  String? _error;
  bool _obscureOld = true;
  bool _obscureNew = true;
  bool _obscureConfirm = true;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.getCurrentUser();
      setState(() {
        _userInfo = response['data'] ?? response;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _changePassword() async {
    if (!_passwordFormKey.currentState!.validate()) return;
    setState(() => _isChangingPassword = true);
    try {
      await _api.post('auth/change-password', data: {
        'old_password': _oldPasswordController.text,
        'new_password': _newPasswordController.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم تغيير كلمة المرور بنجاح'), backgroundColor: AppColors.success),
        );
        _oldPasswordController.clear();
        _newPasswordController.clear();
        _confirmPasswordController.clear();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    } finally {
      if (mounted) setState(() => _isChangingPassword = false);
    }
  }

  @override
  void dispose() {
    _oldPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الملف الشخصي'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadProfile,
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
                TextButton(onPressed: _loadProfile, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      AppCard(
                        child: Column(
                          children: [
                            CircleAvatar(
                              radius: 48,
                              backgroundColor: AppColors.primaryContainer,
                              child: Icon(
                                Icons.person,
                                size: 48,
                                color: AppColors.primary,
                              ),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              _userInfo?['username'] ?? '',
                              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _userInfo?['email'] ?? '',
                              style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
                            ),
                            const SizedBox(height: 12),
                            if (_userInfo?['roles'] != null)
                              Wrap(
                                spacing: 8,
                                runSpacing: 4,
                                alignment: WrapAlignment.center,
                                children: (_userInfo!['roles'] is List
                                        ? _userInfo!['roles']
                                        : [_userInfo!['roles']])
                                    .map<Widget>((role) => Chip(
                                          label: Text(role.toString(), style: const TextStyle(fontSize: 12)),
                                          visualDensity: VisualDensity.compact,
                                        ))
                                    .toList(),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 24),
                      AppCard(
                        child: Form(
                            key: _passwordFormKey,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                const Text(
                                  'تغيير كلمة المرور',
                                  style: AppTextStyles.headlineSmall,
                                ),
                                const SizedBox(height: 16),
                                TextFormField(
                                  controller: _oldPasswordController,
                                  obscureText: _obscureOld,
                                  decoration: InputDecoration(
                                    labelText: 'كلمة المرور الحالية',
                                    border: const OutlineInputBorder(
                                      borderSide: BorderSide(color: AppColors.inputBorder),
                                      borderRadius: BorderRadius.all(Radius.circular(AppDimens.radiusInput)),
                                    ),
                                    prefixIcon: const Icon(Icons.lock_outline),
                                    suffixIcon: IconButton(
                                      icon: Icon(_obscureOld ? Icons.visibility_off : Icons.visibility),
                                      onPressed: () => setState(() => _obscureOld = !_obscureOld),
                                    ),
                                  ),
                                  validator: (v) {
                                    if (v == null || v.isEmpty) return 'مطلوب';
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 16),
                                TextFormField(
                                  controller: _newPasswordController,
                                  obscureText: _obscureNew,
                                  decoration: InputDecoration(
                                    labelText: 'كلمة المرور الجديدة',
                                    border: const OutlineInputBorder(
                                      borderSide: BorderSide(color: AppColors.inputBorder),
                                      borderRadius: BorderRadius.all(Radius.circular(AppDimens.radiusInput)),
                                    ),
                                    prefixIcon: const Icon(Icons.lock),
                                    suffixIcon: IconButton(
                                      icon: Icon(_obscureNew ? Icons.visibility_off : Icons.visibility),
                                      onPressed: () => setState(() => _obscureNew = !_obscureNew),
                                    ),
                                  ),
                                  validator: (v) {
                                    if (v == null || v.isEmpty) return 'مطلوب';
                                    if (v.length < 10) return 'يجب أن تكون كلمة المرور 10 أحرف على الأقل';
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 16),
                                TextFormField(
                                  controller: _confirmPasswordController,
                                  obscureText: _obscureConfirm,
                                  decoration: InputDecoration(
                                    labelText: 'تأكيد كلمة المرور الجديدة',
                                    border: const OutlineInputBorder(
                                      borderSide: BorderSide(color: AppColors.inputBorder),
                                      borderRadius: BorderRadius.all(Radius.circular(AppDimens.radiusInput)),
                                    ),
                                    prefixIcon: const Icon(Icons.lock),
                                    suffixIcon: IconButton(
                                      icon: Icon(_obscureConfirm ? Icons.visibility_off : Icons.visibility),
                                      onPressed: () => setState(() => _obscureConfirm = !_obscureConfirm),
                                    ),
                                  ),
                                  validator: (v) {
                                    if (v == null || v.isEmpty) return 'مطلوب';
                                    if (v != _newPasswordController.text) return 'كلمتا المرور غير متطابقتين';
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 24),
                                AppButton(
                                  label: 'تغيير كلمة المرور',
                                  onPressed: _isChangingPassword ? null : _changePassword,
                                  icon: Icons.save,
                                  loading: _isChangingPassword,
                                  expanded: true,
                                  variant: AppButtonVariant.success,
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
          ),
        ],
      ),
    );
  }
}
