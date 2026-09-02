import '../services/api_service.dart';

/// Shared currency helper — fetches currencies and base currency from app settings.
class CurrencyHelper {
  static List<Map<String, dynamic>> _cachedCurrencies = [];
  static String _cachedBaseCurrency = 'USD';
  static bool _loaded = false;

  /// Load currencies and base currency from API.
  static Future<void> load() async {
    try {
      final api = ApiService();
      final response = await api.get('currency');
      final items = response['items'] ?? [];
      if (items is List) {
        _cachedCurrencies = items.cast<Map<String, dynamic>>();
      }
      // Try to find base currency
      for (final c in _cachedCurrencies) {
        if (c['is_base'] == true || c['is_base'] == 'true') {
          _cachedBaseCurrency = (c['code'] ?? 'USD').toString();
          break;
        }
      }
      _loaded = true;
    } catch (_) {
      if (!_loaded) {
        _cachedBaseCurrency = 'USD';
        _loaded = true;
      }
    }
  }

  /// Get all currencies.
  static List<Map<String, dynamic>> get currencies => _cachedCurrencies;

  /// Get base currency code.
  static String get baseCurrency => _cachedBaseCurrency;

  /// Get currency codes as list of strings.
  static List<String> get currencyCodes =>
      _cachedCurrencies.map((c) => (c['code'] ?? '').toString()).where((s) => s.isNotEmpty).toList();

  /// Get dropdown items.
  static List<DropdownCurrencyItem> get dropdownItems =>
      _cachedCurrencies.map((c) => DropdownCurrencyItem(
            code: (c['code'] ?? '').toString(),
            name: (c['name'] ?? '').toString(),
            symbol: (c['symbol'] ?? '').toString(),
          )).where((i) => i.code.isNotEmpty).toList();
}

class DropdownCurrencyItem {
  final String code;
  final String name;
  final String symbol;

  const DropdownCurrencyItem({required this.code, required this.name, required this.symbol});
}
