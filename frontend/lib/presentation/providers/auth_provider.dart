import 'package:flutter/foundation.dart';
import '../../services/api_client.dart';
import '../../utils/error_utils.dart';

class AuthProvider extends ChangeNotifier {
  Map<String, dynamic>? _user;
  bool _isLoading = false;
  String? _error;

  Map<String, dynamic>? get user => _user;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _user != null;
  String? get username => _user?['username'];
  List<String> get roles => List<String>.from(_user?['roles'] ?? []);
  List<String> get permissions => List<String>.from(_user?['permissions'] ?? []);

  bool get isSuperAdmin => _user?['is_super_admin'] == true;

  /// يعرّف ما إذا كان المستخدم يملك صلاحية ما.
  ///
  /// يدعم التطابق المباشر، أو بأي بادئة مقطع/فئة:
  /// مثلًا "settings.manage_users" يطابق "manage_users"،
  /// و "accounting.post_entry" يطابق "post_entry".
  bool hasPermission(String permission) {
    final code = _suffix(permission);
    return permissions.contains(permission) ||
        permissions.contains(code) ||
        permissions.any((p) => _suffix(p) == code);
  }

  bool hasAnyPermission(List<String> accepted) {
    return accepted.any(hasPermission);
  }

  /// يستخرج الجزء الأخير بعد آخر نقطة، أو يعيد النص كما هو.
  static String _suffix(String value) {
    final idx = value.lastIndexOf('.');
    return idx == -1 ? value : value.substring(idx + 1);
  }

  bool hasRole(String role) {
    return roles.contains(role);
  }

  void setUser(Map<String, dynamic> user) {
    _user = user;
    notifyListeners();
  }

  Future<void> loadCurrentUser() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final user = await ApiClient().getCurrentUser();
      if (user != null) {
        _user = user;
      }
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    try {
      await ApiClient().logout();
    } catch (e) {
      // تجاهل الأخطاء
    } finally {
      _user = null;
      notifyListeners();
    }
  }

  Future<bool> changePassword(String oldPassword, String newPassword) async {
    try {
      await ApiClient().changePassword(oldPassword, newPassword);
      return true;
    } catch (e) {
      _error = ErrorUtils.sanitize(e);
      notifyListeners();
      return false;
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}