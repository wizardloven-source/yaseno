import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../presentation/widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';

class SitesScreen extends StatefulWidget {
  const SitesScreen({super.key});

  @override
  State<SitesScreen> createState() => _SitesScreenState();
}

class _SitesScreenState extends State<SitesScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _sites = [];
  bool _isLoading = true;
  String? _error;

  String? _defaultSiteId;
  final _searchController = TextEditingController();
  String _searchText = '';

  final _codeController = TextEditingController();
  final _nameController = TextEditingController();
  final _cityController = TextEditingController();
  final _streetController = TextEditingController();
  final _countryController = TextEditingController();
  final _phoneController = TextEditingController();
  final _mobileController = TextEditingController();
  final _emailController = TextEditingController();
  String _selectedType = 'branch';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _codeController.dispose();
    _nameController.dispose();
    _cityController.dispose();
    _streetController.dispose();
    _countryController.dispose();
    _phoneController.dispose();
    _mobileController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('sites',
          queryParameters: {'include_inactive': true});
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];

      String? defaultId;
      try {
        final defaultRes = await _api.get('sites/default');
        final defaultData = defaultRes['data'];
        defaultId = defaultData is Map ? defaultData['id']?.toString() : null;
      } catch (_) {}

      setState(() {
        _sites = (items as List).cast<Map<String, dynamic>>();
        _defaultSiteId = defaultId;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _search(String query) async {
    setState(() {
      _searchText = query.trim();
      _isLoading = true;
      _error = null;
    });
    try {
      if (_searchText.isEmpty) {
        await _loadData();
        return;
      }
      final response = await _api.get('sites/search',
          queryParameters: {'q': _searchText, 'limit': 100});
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _sites = (items as List).cast<Map<String, dynamic>>();
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
      case 'warehouse':
        return 'مستودع';
      case 'branch':
        return 'فرع';
      case 'office':
        return 'مكتب';
      default:
        return type;
    }
  }

  void _showSiteDialog({Map<String, dynamic>? site}) {
    final isEdit = site != null;
    _codeController.text = site?['code'] ?? '';
    _nameController.text = site?['name'] ?? '';
    _cityController.text = site?['city'] ?? '';
    _streetController.text = site?['street'] ?? '';
    _countryController.text = site?['country'] ?? '';
    _phoneController.text = site?['phone'] ?? '';
    _mobileController.text = site?['mobile'] ?? '';
    _emailController.text = site?['email'] ?? '';
    _selectedType = site?['site_type'] ?? site?['type'] ?? 'branch';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(isEdit ? 'تعديل الموقع' : 'إضافة موقع'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!isEdit)
                TextField(
                  controller: _codeController,
                  decoration: const InputDecoration(
                    labelText: 'الرمز',
                    hintText: 'مثال: BR-001',
                  ),
                ),
              const SizedBox(height: 12),
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'الاسم',
                  hintText: 'مثال: الفرع الرئيسي',
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _selectedType,
                decoration: const InputDecoration(labelText: 'النوع'),
                items: const [
                  DropdownMenuItem(value: 'branch', child: Text('فرع')),
                  DropdownMenuItem(value: 'warehouse', child: Text('مستودع')),
                  DropdownMenuItem(value: 'office', child: Text('مكتب')),
                ],
                onChanged: (v) {
                  if (v != null) _selectedType = v;
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _streetController,
                decoration: const InputDecoration(labelText: 'العنوان / الشارع'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _cityController,
                decoration: const InputDecoration(labelText: 'المدينة'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _countryController,
                decoration: const InputDecoration(labelText: 'الدولة'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _phoneController,
                decoration: const InputDecoration(labelText: 'الهاتف'),
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _mobileController,
                decoration: const InputDecoration(labelText: 'الجوال'),
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _emailController,
                decoration: const InputDecoration(labelText: 'البريد الإلكتروني'),
                keyboardType: TextInputType.emailAddress,
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
            onPressed: () => _saveSite(ctx, site),
          ),
        ],
      ),
    );
  }

  Future<void> _saveSite(BuildContext dialogContext, Map<String, dynamic>? site) async {
    final id = site?['id'];
    final data = <String, dynamic>{
      'name': _nameController.text.trim(),
      'site_type': _selectedType,
      'street': _streetController.text.trim(),
      'city': _cityController.text.trim(),
      'country': _countryController.text.trim(),
      'phone': _phoneController.text.trim(),
      'mobile': _mobileController.text.trim(),
      'email': _emailController.text.trim(),
    };

    if ((data['name'] ?? '').toString().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('الاسم مطلوب')),
      );
      return;
    }

    try {
      if (id != null) {
        data['version'] = site?['version'] ?? 1;
        await _api.put('sites/$id', data: data);
      } else {
        data['code'] = _codeController.text.trim();
        if ((data['code'] ?? '').toString().isEmpty) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('الرمز مطلوب')),
          );
          return;
        }
        await _api.post('sites', data: data);
      }
      Navigator.pop(dialogContext);
      if (_searchText.isNotEmpty) {
        _search(_searchText);
      } else {
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Future<void> _toggleActive(Map<String, dynamic> site) async {
    final id = site['id'];
    final current = site['is_active'] == true;
    try {
      await _api.put('sites/$id', data: {
        'name': site['name'] ?? '',
        'site_type': site['site_type'] ?? site['type'] ?? 'branch',
        'street': site['street'],
        'city': site['city'],
        'country': site['country'],
        'phone': site['phone'],
        'mobile': site['mobile'],
        'email': site['email'],
        'is_active': !current,
        'version': site['version'] ?? 1,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(current ? 'تم إيقاف الموقع' : 'تم تفعيل الموقع'),
            backgroundColor: AppColors.success,
          ),
        );
      }
      if (_searchText.isNotEmpty) {
        _search(_searchText);
      } else {
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  void _showStatistics(Map<String, dynamic> site) async {
    final id = site['id'];
    try {
      final response = await _api.get('sites/$id/statistics');
      final data = response['data'] ?? {};
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) {
            final stats = data['statistics'] is Map
                ? (data['statistics'] as Map)
                : <dynamic, dynamic>{};
            final invoices = stats['invoices'] is Map
                ? (stats['invoices'] as Map)
                : <dynamic, dynamic>{};
            final purchases = stats['purchase_orders'] is Map
                ? (stats['purchase_orders'] as Map)
                : <dynamic, dynamic>{};
            return AlertDialog(
              title: Text('إحصائيات ${site['name'] ?? ''}'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _statRow('إجمالي المعاملات',
                      '${stats['total_transactions'] ?? 0}'),
                  _statRow('إجمالي المبلغ', _fmt(stats['total_amount'])),
                  const Divider(),
                  Text('الفواتير', style: AppTextStyles.titleSmall),
                  _statRow('عدد الفواتير', '${invoices['total_invoices'] ?? 0}'),
                  _statRow('إجمالي الفواتير', _fmt(invoices['total_amount'])),
                  _statRow('متوسط الفاتورة', _fmt(invoices['average_amount'])),
                  const Divider(),
                  Text('أوامر الشراء', style: AppTextStyles.titleSmall),
                  _statRow('عدد الأوامر', '${purchases['total_orders'] ?? 0}'),
                  _statRow('إجمالي الأوامر', _fmt(purchases['total_amount'])),
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

  Widget _statRow(String label, String value) {
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

  Future<void> _deleteSite(String id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('حذف الموقع'),
        content: const Text('هل أنت متأكد من حذف هذا الموقع؟'),
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
      await _api.delete('sites/$id');
      _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  Future<void> _setAsDefault(String id) async {
    try {
      await _api.post('sites/$id/default');
      _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e))));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('إدارة المواقع'),
        centerTitle: true,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
        ],
      ),
      body: _buildBody(),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showSiteDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const LoadingState();
    return Column(
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
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: TextField(
            controller: _searchController,
            onSubmitted: _search,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'بحث عن موقع...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchText.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                        _search('');
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppDimens.radiusInput),
              ),
              isDense: true,
            ),
          ),
        ),
        if (_sites.isEmpty && _error == null)
          const Expanded(
            child: EmptyState(
              icon: Icons.location_city,
              title: 'لا توجد مواقع',
            ),
          )
        else if (_sites.isNotEmpty)
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadData,
              child: ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: _sites.length,
                itemBuilder: (context, index) {
                  final site = _sites[index];
                  final isDefault =
                      site['id']?.toString() == _defaultSiteId ||
                      site['is_default'] == true;
                  final isActive = site['is_active'] == true;
                  final type = site['site_type'] ?? site['type'] ?? 'branch';
                  final city = site['city'] ?? '';
                  final street = site['street'] ?? '';
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    color: isActive ? null : AppColors.surfaceVariant,
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: isDefault
                            ? AppColors.successContainer
                            : AppColors.secondaryContainer,
                        child: Icon(Icons.location_city,
                            color: isDefault ? AppColors.success : AppColors.secondary),
                      ),
                      title: Row(
                        children: [
                          Expanded(
                            child: Text('${site['name'] ?? ''}',
                                style: const TextStyle(fontWeight: FontWeight.bold)),
                          ),
                          if (!isActive)
                            Container(
                              margin: const EdgeInsets.only(right: 4),
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppColors.buttonCancel,
                                borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                              ),
                              child: const Text('غير مفعل',
                                  style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold)),
                            ),
                          if (isDefault)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppColors.success,
                                borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                              ),
                              child: const Text('افتراضي',
                                  style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold)),
                            ),
                        ],
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('الرمز: ${site['code'] ?? ''} · النوع: ${_typeLabel(type)}'),
                          if ((street as String).isNotEmpty ||
                              (city as String).isNotEmpty)
                            Text('العنوان: $street${(street as String).isNotEmpty && (city as String).isNotEmpty ? ' - ' : ''}$city'),
                        ],
                      ),
                      trailing: PopupMenuButton(
                        itemBuilder: (ctx) => [
                          const PopupMenuItem(
                              value: 'edit', child: Text('تعديل')),
                          const PopupMenuItem(
                              value: 'stats', child: Text('الإحصائيات')),
                          if (!isDefault)
                            const PopupMenuItem(
                                value: 'default', child: Text('تعيين كافتراضي')),
                          PopupMenuItem(
                              value: 'toggle',
                              child: Text(isActive ? 'إيقاف الموقع' : 'تفعيل الموقع')),
                          const PopupMenuItem(
                              value: 'delete',
                              child: Text('حذف',
                                  style: TextStyle(color: AppColors.danger))),
                        ],
                        onSelected: (v) {
                          if (v == 'edit') {
                            _showSiteDialog(site: site);
                          } else if (v == 'stats') {
                            _showStatistics(site);
                          } else if (v == 'default') {
                            _setAsDefault(site['id']);
                          } else if (v == 'toggle') {
                            _toggleActive(site);
                          } else if (v == 'delete') {
                            _deleteSite(site['id']);
                          }
                        },
                      ),
                      onTap: () => _showSiteDialog(site: site),
                    ),
                  );
                },
              ),
            ),
          )
        else
          const Expanded(child: SizedBox.shrink()),
      ],
    );
  }
}
