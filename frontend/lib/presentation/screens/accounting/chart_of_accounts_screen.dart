import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../services/api_service.dart';
import '../../../domain/entities/account.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/error_logger.dart';
import '../../../utils/money_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';

class ChartOfAccountsScreen extends StatefulWidget {
  const ChartOfAccountsScreen({super.key});

  @override
  State<ChartOfAccountsScreen> createState() => _ChartOfAccountsScreenState();
}

class _ChartOfAccountsScreenState extends State<ChartOfAccountsScreen> {
  final ApiService _api = ApiService();
  List<Account> _accounts = [];
  bool _isLoading = true;
  String? _error;
  String _searchQuery = '';
  String? _selectedType;
  String _currencySymbol = 'د.ع';

  @override
  void initState() {
    super.initState();
    _loadBaseCurrency();
    _loadAccounts();
  }

  Future<void> _loadBaseCurrency() async {
    try {
      final res = await _api.get('currency/base');
      final data = res['data'];
      if (data is Map && mounted) {
        setState(() => _currencySymbol = data['symbol'] ?? 'د.ع');
      }
    } catch (e, s) {
      await ErrorLogger.log('chart_base_currency', e, s);
    }
  }

  Future<void> _loadAccounts() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('accounts');
      final data = response['data'] ?? response;
      final items = (data is Map ? data['accounts'] ?? data['items'] : data) ?? [];
      final flat = (items as List)
          .map((e) => Account.fromJson((e as Map).cast<String, dynamic>()))
          .toList();
      if (!mounted) return;
      setState(() {
        _accounts = _buildTree(flat);
        _isLoading = false;
      });
    } catch (e, s) {
      await ErrorLogger.log('chart_load_accounts', e, s);
      if (!mounted) return;
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  List<Account> _buildTree(List<Account> flat) {
    final byCode = <String, Account>{for (final a in flat) a.code: a};
    final childrenByParent = <String, List<Account>>{};
    for (final a in flat) {
      final parent = a.parentCode;
      if (parent != null && parent.isNotEmpty && byCode.containsKey(parent)) {
        childrenByParent.putIfAbsent(parent, () => []).add(a);
      }
    }
    Account attach(Account acc) {
      final kids = childrenByParent[acc.code];
      if (kids == null || kids.isEmpty) return acc;
      return acc.copyWith(children: kids.map(attach).toList());
    }

    return flat
        .where((a) {
          final parent = a.parentCode;
          return parent == null || parent.isEmpty || !byCode.containsKey(parent);
        })
        .map(attach)
        .toList();
  }

  List<Account> _filterNodes(List<Account> nodes) {
    final result = <Account>[];
    for (final n in nodes) {
      final kids = n.children == null ? null : _filterNodes(n.children!);
      final selfMatch = _matchesFilter(n);
      if (kids != null && kids.isNotEmpty) {
        result.add(n.copyWith(children: kids));
      } else if (selfMatch) {
        result.add(n.copyWith(children: const []));
      }
    }
    return result;
  }

  bool _matchesFilter(Account acc) {
    if (_searchQuery.trim().isNotEmpty) {
      final q = _searchQuery.trim().toLowerCase();
      if (!acc.name.toLowerCase().contains(q) &&
          !acc.code.toLowerCase().contains(q)) {
        return false;
      }
    }
    if (_selectedType != null && acc.accountType != _selectedType) return false;
    return true;
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'asset':
        return 'أصول';
      case 'liability':
        return 'خصوم';
      case 'equity':
        return 'حقوق ملكية';
      case 'revenue':
        return 'إيرادات';
      case 'expense':
        return 'مصروفات';
      default:
        return type;
    }
  }

  void _handleMenu(String value, Account acc) {
    if (value == 'edit') {
      context.go('/accounts/${acc.code}/edit');
    } else if (value == 'child') {
      context.go('/accounts/create?parent=${acc.code}');
    }
  }

  void _showAccountActions(Account acc) {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.edit_outlined),
              title: const Text('تعديل'),
              onTap: () {
                Navigator.pop(ctx);
                context.go('/accounts/${acc.code}/edit');
              },
            ),
            ListTile(
              leading: const Icon(Icons.account_tree_outlined),
              title: const Text('إنشاء حساب فرعي'),
              onTap: () {
                Navigator.pop(ctx);
                context.go('/accounts/create?parent=${acc.code}');
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _avatar(Account acc) {
    return CircleAvatar(
      backgroundColor: acc.typeColor.withOpacity(0.1),
      child: Text(
        acc.code.length >= 2 ? acc.code.substring(0, 2) : acc.code,
        style: TextStyle(
          color: acc.typeColor,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _accountTitle(Account acc) {
    return Row(
      children: [
        Expanded(
          child: Text(
            acc.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
        ),
        if (acc.balance != null) ...[
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: acc.typeColor.withOpacity(0.08),
              borderRadius: BorderRadius.circular(AppDimens.radiusCard),
            ),
            child: Text(
              formatMoneyCurrency(acc.balance, currency: _currencySymbol),
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: acc.typeColor,
              ),
            ),
          ),
        ],
        PopupMenuButton<String>(
          tooltip: 'إجراءات',
          onSelected: (v) => _handleMenu(v, acc),
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'edit', child: Text('تعديل')),
            PopupMenuItem(value: 'child', child: Text('إنشاء حساب فرعي')),
          ],
        ),
      ],
    );
  }

  Widget _accountSubtitle(Account acc) {
    return Text('${acc.code} · ${acc.typeDisplay}');
  }

  List<Widget> _buildNodes(List<Account> nodes) {
    return nodes.map((acc) {
      final hasChildren = acc.children != null && acc.children!.isNotEmpty;
      if (hasChildren) {
        return ExpansionTile(
          key: PageStorageKey(acc.code),
          leading: _avatar(acc),
          title: _accountTitle(acc),
          subtitle: _accountSubtitle(acc),
          children: _buildNodes(acc.children!),
        );
      }
      return ListTile(
        leading: _avatar(acc),
        title: _accountTitle(acc),
        subtitle: _accountSubtitle(acc),
        onTap: () => _showAccountActions(acc),
        onLongPress: () => _showAccountActions(acc),
      );
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('دليل الحسابات'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadAccounts,
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
                TextButton(onPressed: _loadAccounts, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    decoration: const InputDecoration(
                      hintText: 'بحث بالاسم أو الرمز...',
                      prefixIcon: Icon(Icons.search),
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    onChanged: (v) => setState(() => _searchQuery = v),
                  ),
                ),
                const SizedBox(width: 8),
                DropdownButton<String?>(
                  value: _selectedType,
                  hint: const Text('النوع'),
                  items: [
                    const DropdownMenuItem(value: null, child: Text('الكل')),
                    ...['asset', 'liability', 'equity', 'revenue', 'expense']
                        .map((t) => DropdownMenuItem(
                            value: t, child: Text(_typeLabel(t)))),
                  ],
                  onChanged: (v) => setState(() => _selectedType = v),
                ),
              ],
            ),
          ),
          Expanded(child: _buildBody()),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.go('/accounts/create'),
        icon: const Icon(Icons.add),
        label: const Text('إضافة حساب'),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    final visible = _filterNodes(_accounts);
    if (visible.isEmpty) return const Center(child: Text('لا توجد حسابات'));
    return ListView(
      padding: const EdgeInsets.all(8),
      children: _buildNodes(visible),
    );
  }
}