import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// إدارة وضع المظهر (فاتح / داكن / تلقائي) مع حفظه محلياً.
class ThemeProvider extends ChangeNotifier {
  static const _prefsKey = 'app_theme_mode';

  ThemeMode _mode = ThemeMode.system;

  ThemeMode get mode => _mode;

  String get modeAsString {
    switch (_mode) {
      case ThemeMode.light:
        return 'light';
      case ThemeMode.dark:
        return 'dark';
      default:
        return 'system';
    }
  }

  /// يقرأ الوضع المحفوظ محلياً عند بدء التشغيل.
  Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_prefsKey);
      switch (saved) {
        case 'light':
          _mode = ThemeMode.light;
          break;
        case 'dark':
          _mode = ThemeMode.dark;
          break;
        default:
          _mode = ThemeMode.system;
      }
      notifyListeners();
    } catch (_) {}
  }

  /// يضبط الوضع من قيمة نصية ('system' / 'light' / 'dark') ويحفظه محلياً.
  Future<void> setMode(String value) async {
    switch (value) {
      case 'light':
        _mode = ThemeMode.light;
        break;
      case 'dark':
        _mode = ThemeMode.dark;
        break;
      default:
        _mode = ThemeMode.system;
    }
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefsKey, value);
    } catch (_) {}
  }
}
