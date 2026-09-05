import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../utils/error_utils.dart';
import '../../widgets/app_widgets.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/empty_state.dart';

class AssetsScreen extends StatefulWidget {
  const AssetsScreen({super.key});

  @override
  State<AssetsScreen> createState() => _AssetsScreenState();
}

class _AssetsScreenState extends State<AssetsScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _assets = [];
  bool _isLoading = true;
  String? _error;
  String? _filterType;
  String? _filterStatus;
  bool _includeInactive = false;
  int _page = 1;
  int _totalPages = 1;

  static const List<String> _assetTypes = [
    'أثاث ومفروشات',
    'أجهزة ومعدات',
    'مركبات',
    'عقارات',
    'أجهزة كمبيوتر',
    'أدوات',
    'أخرى',
  ];

  static const List<String> _depreciationMethods = [
    'straight_line',
    'declining_balance',
    'units_of_production',
  ];

  static const Map<String, String> _depreciationMethodLabels = {
    'straight_line': 'القسط الثابت',
    'declining_balance': 'القسط المتناقص',
    'units_of_production': 'حسب الإنتاج',
  };

  static const Map<String, String> _assetTypeLabels = {
    'furniture': 'أثاث ومفروشات',
    'equipment': 'أجهزة ومعدات',
    'vehicle': 'مركبات',
    'building': 'عقارات',
    'computer': 'أجهزة كمبيوتر',
    'tools': 'أدوات',
    'other': 'أخرى',
  };

  @override
  void initState() {
    super.initState();
    _loadAssets();
  }

  Future<void> _loadAssets() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final params = <String, dynamic>{
        'page': _page,
        'limit': 20,
        'inactive': _includeInactive,
      };
      if (_filterType != null) params['asset_type'] = _filterType;
      if (_filterStatus != null) params['status'] = _filterStatus;

      final response = await _api.get('assets', queryParameters: params);
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      final total = (data is Map && data['total_pages'] != null)
          ? data['total_pages']
          : 1;
      setState(() {
        _assets = (items as List).cast<Map<String, dynamic>>();
        _totalPages = total is int ? total : 1;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppColors.danger),
    );
  }

  void _showSuccess(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppColors.success),
    );
  }

  // ── Create Asset ──────────────────────────────────────────────────────────

  Future<void> _showCreateAssetDialog() async {
    final nameCtrl = TextEditingController();
    final codeCtrl = TextEditingController();
    final costCtrl = TextEditingController();
    final lifeCtrl = TextEditingController();
    final locationCtrl = TextEditingController();
    final supplierCtrl = TextEditingController();
    final notesCtrl = TextEditingController();
    String? selectedType = 'equipment';
    String? selectedDepMethod = 'straight_line';
    DateTime acquisitionDate = DateTime.now();

    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom,
            left: 16,
            right: 16,
            top: 16,
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'إضافة أصل جديد',
                  style: AppTextStyles.headlineSmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(
                    labelText: 'اسم الأصل *',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.label),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: codeCtrl,
                  decoration: const InputDecoration(
                    labelText: 'كود الأصل *',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.qr_code),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: selectedType,
                  decoration: const InputDecoration(
                    labelText: 'نوع الأصل *',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.category),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'furniture', child: Text('أثاث ومفروشات')),
                    DropdownMenuItem(value: 'equipment', child: Text('أجهزة ومعدات')),
                    DropdownMenuItem(value: 'vehicle', child: Text('مركبات')),
                    DropdownMenuItem(value: 'building', child: Text('عقارات')),
                    DropdownMenuItem(value: 'computer', child: Text('أجهزة كمبيوتر')),
                    DropdownMenuItem(value: 'tools', child: Text('أدوات')),
                    DropdownMenuItem(value: 'other', child: Text('أخرى')),
                  ],
                  onChanged: (v) => setSheetState(() => selectedType = v),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: costCtrl,
                  decoration: const InputDecoration(
                    labelText: 'التكلفة *',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.monetization_on),
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 12),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('تاريخ الاستحواذ'),
                  subtitle: Text(
                    '${acquisitionDate.year}-${acquisitionDate.month.toString().padLeft(2, '0')}-${acquisitionDate.day.toString().padLeft(2, '0')}',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: acquisitionDate,
                      firstDate: DateTime(2000),
                      lastDate: DateTime.now(),
                    );
                    if (picked != null) {
                      setSheetState(() => acquisitionDate = picked);
                    }
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: lifeCtrl,
                  decoration: const InputDecoration(
                    labelText: 'العمر الإنتاجي (سنوات)',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.timer),
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: selectedDepMethod,
                  decoration: const InputDecoration(
                    labelText: 'طريقة الإطفاء',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.trending_down),
                  ),
                  items: _depreciationMethods
                      .map((m) => DropdownMenuItem(
                            value: m,
                            child: Text(_depreciationMethodLabels[m] ?? m),
                          ))
                      .toList(),
                  onChanged: (v) => setSheetState(() => selectedDepMethod = v),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: locationCtrl,
                  decoration: const InputDecoration(
                    labelText: 'الموقع',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.location_on),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: supplierCtrl,
                  decoration: const InputDecoration(
                    labelText: 'كود المورد',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.business),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: notesCtrl,
                  decoration: const InputDecoration(
                    labelText: 'ملاحظات',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.notes),
                  ),
                  maxLines: 2,
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: AppButton(
                        onPressed: () => Navigator.pop(ctx, false),
                        label: 'إلغاء',
                        variant: AppButtonVariant.cancel,
                        expanded: true,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: AppButton(
                        onPressed: () {
                          if (nameCtrl.text.isEmpty || codeCtrl.text.isEmpty || costCtrl.text.isEmpty) {
                            ScaffoldMessenger.of(ctx).showSnackBar(
                              const SnackBar(content: Text('يرجى ملء الحقول المطلوبة')),
                            );
                            return;
                          }
                          Navigator.pop(ctx, true);
                          _createAsset(
                            name: nameCtrl.text,
                            code: codeCtrl.text,
                            assetType: selectedType ?? 'equipment',
                            cost: double.tryParse(costCtrl.text) ?? 0,
                            acquisitionDate: acquisitionDate,
                            usefulLifeYears: int.tryParse(lifeCtrl.text),
                            depreciationMethod: selectedDepMethod,
                            location: locationCtrl.text.isNotEmpty ? locationCtrl.text : null,
                            supplierId: supplierCtrl.text.isNotEmpty ? supplierCtrl.text : null,
                            notes: notesCtrl.text.isNotEmpty ? notesCtrl.text : null,
                          );
                        },
                        label: 'حفظ',
                        variant: AppButtonVariant.success,
                        expanded: true,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _createAsset({
    required String name,
    required String code,
    required String assetType,
    required double cost,
    required DateTime acquisitionDate,
    int? usefulLifeYears,
    String? depreciationMethod,
    String? location,
    String? supplierId,
    String? notes,
  }) async {
    try {
      await _api.post('assets', data: {
        'name': name,
        'code': code,
        'asset_type': assetType,
        'cost': cost,
        'acquisition_date':
            '${acquisitionDate.year}-${acquisitionDate.month.toString().padLeft(2, '0')}-${acquisitionDate.day.toString().padLeft(2, '0')}',
        if (usefulLifeYears != null) 'useful_life_years': usefulLifeYears,
        if (depreciationMethod != null) 'depreciation_method': depreciationMethod,
        if (location != null) 'location': location,
        if (supplierId != null) 'supplier_id': supplierId,
        if (notes != null) 'notes': notes,
      });
      _showSuccess('تم إضافة الأصل بنجاح');
      _loadAssets();
    } catch (e) {
      _showError('خطأ في إضافة الأصل: ${ErrorUtils.sanitize(e)}');
    }
  }

  // ── Asset Detail ──────────────────────────────────────────────────────────

  Future<void> _viewAssetDetail(Map<String, dynamic> asset) async {
    final id = asset['id'];
    try {
      final response = await _api.get('assets/$id');
      final detail = response['data'] ?? response;
      if (!mounted) return;
      showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        builder: (ctx) => DraggableScrollableSheet(
          initialChildSize: 0.7,
          maxChildSize: 0.95,
          minChildSize: 0.4,
          expand: false,
          builder: (ctx, scrollCtrl) => ListView(
            controller: scrollCtrl,
            padding: const EdgeInsets.all(16),
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Text(
                '${detail['name'] ?? ''}',
                style: AppTextStyles.headlineLarge,
              ),
              const SizedBox(height: 4),
              Chip(
                label: Text(
                  detail['status'] == 'disposed' ? 'تم التخلص' : 'نشط',
                  style: TextStyle(
                    color: detail['status'] == 'disposed'
                        ? AppColors.warning
                        : AppColors.success,
                  ),
                ),
                backgroundColor: detail['status'] == 'disposed'
                    ? AppColors.warningContainer
                    : AppColors.successContainer,
              ),
              const Divider(height: 24),
              _detailRow('الكود', '${detail['code'] ?? ''}'),
              _detailRow('النوع', _assetTypeLabels[detail['asset_type']] ?? '${detail['asset_type'] ?? ''}'),
              _detailRow('التكلفة', '${detail['cost'] ?? 0}'),
              _detailRow('تاريخ الاستحواذ', '${detail['acquisition_date'] ?? ''}'),
              _detailRow('العمر الإنتاجي', detail['useful_life_years'] != null ? '${detail['useful_life_years']} سنة' : '-'),
              _detailRow('طريقة الإطفاء', _depreciationMethodLabels[detail['depreciation_method']] ?? '${detail['depreciation_method'] ?? '-'}'),
              _detailRow('الموقع', '${detail['location'] ?? '-'}'),
              _detailRow('القيمة الدفترية', '${detail['book_value'] ?? '-'}'),
              _detailRow('الإطفاء المتراكم', '${detail['accumulated_depreciation'] ?? '-'}'),
              if (detail['notes'] != null && '${detail['notes']}'.isNotEmpty)
                _detailRow('ملاحظات', '${detail['notes']}'),
              const SizedBox(height: 16),
              if (detail['status'] != 'disposed') ...[
                Row(
                  children: [
                    Expanded(
                      child: AppButton(
                        onPressed: () {
                          Navigator.pop(ctx);
                          _postDepreciation(id);
                        },
                        icon: Icons.trending_down,
                        label: 'تسجيل إطفاء',
                        variant: AppButtonVariant.primary,
                        expanded: true,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: AppButton(
                        onPressed: () {
                          Navigator.pop(ctx);
                          _disposeAsset(id);
                        },
                        icon: Icons.delete_forever,
                        label: 'إخلاء',
                        variant: AppButtonVariant.danger,
                        expanded: true,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      );
    } catch (e) {
      _showError('خطأ في تحميل تفاصيل الأصل: ${ErrorUtils.sanitize(e)}');
    }
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          Flexible(
            child: Text(value, style: AppTextStyles.titleSmall),
          ),
        ],
      ),
    );
  }

  // ── Run Bulk Depreciation ─────────────────────────────────────────────────

  Future<void> _showRunDepreciationDialog() async {
    DateTime asOfDate = DateTime.now();
    final result = await showModalBottomSheet<bool>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) => Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'تشغيل الإطفاء الشهري',
                style: AppTextStyles.headlineSmall,
              ),
              const SizedBox(height: 16),
              ListTile(
                title: const Text('تاريخ التشغيل'),
                subtitle: Text(
                  '${asOfDate.year}-${asOfDate.month.toString().padLeft(2, '0')}-${asOfDate.day.toString().padLeft(2, '0')}',
                ),
                trailing: const Icon(Icons.calendar_today),
                onTap: () async {
                  final picked = await showDatePicker(
                    context: ctx,
                    initialDate: asOfDate,
                    firstDate: DateTime(2020),
                    lastDate: DateTime.now(),
                  );
                  if (picked != null) setSheetState(() => asOfDate = picked);
                },
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: AppButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      label: 'إلغاء',
                      variant: AppButtonVariant.cancel,
                      expanded: true,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: AppButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      label: 'تشغيل',
                      variant: AppButtonVariant.primary,
                      expanded: true,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
    if (result == true) {
      try {
        await _api.post('assets/run-depreciation', data: {
          'as_of_date':
              '${asOfDate.year}-${asOfDate.month.toString().padLeft(2, '0')}-${asOfDate.day.toString().padLeft(2, '0')}',
        });
        _showSuccess('تم تشغيل الإطفاء الشهري بنجاح');
        _loadAssets();
      } catch (e) {
        _showError('خطأ في تشغيل الإطفاء: ${ErrorUtils.sanitize(e)}');
      }
    }
  }

  // ── Post Depreciation for Single Asset ────────────────────────────────────

  Future<void> _postDepreciation(String assetId) async {
    final periodCtrl = TextEditingController(
      text: '${DateTime.now().year}-${DateTime.now().month.toString().padLeft(2, '0')}',
    );
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تسجيل إطفاء'),
        content: TextField(
          controller: periodCtrl,
          decoration: const InputDecoration(
            labelText: 'الفترة (YYYY-MM)',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('تسجيل'),
          ),
        ],
      ),
    );
    if (result == true) {
      try {
        await _api.post('assets/$assetId/depreciation', data: {
          'period': periodCtrl.text,
        });
        _showSuccess('تم تسجيل الإطفاء بنجاح');
        _loadAssets();
      } catch (e) {
        _showError('خطأ في تسجيل الإطفاء: ${ErrorUtils.sanitize(e)}');
      }
    }
  }

  // ── Dispose Asset ─────────────────────────────────────────────────────────

  Future<void> _disposeAsset(String assetId) async {
    String? disposalType = 'sale';
    DateTime disposalDate = DateTime.now();
    final amountCtrl = TextEditingController();
    final reasonCtrl = TextEditingController();

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('إخلاء الأصل'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  value: disposalType,
                  decoration: const InputDecoration(
                    labelText: 'نوع الإخلاء',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'sale', child: Text('بيع')),
                    DropdownMenuItem(value: 'scrap', child: Text('خردة')),
                  ],
                  onChanged: (v) => setDialogState(() => disposalType = v),
                ),
                const SizedBox(height: 12),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('تاريخ الإخلاء'),
                  subtitle: Text(
                    '${disposalDate.year}-${disposalDate.month.toString().padLeft(2, '0')}-${disposalDate.day.toString().padLeft(2, '0')}',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: disposalDate,
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (picked != null) setDialogState(() => disposalDate = picked);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: amountCtrl,
                  decoration: const InputDecoration(
                    labelText: 'مبلغ الإخلاء',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: reasonCtrl,
                  decoration: const InputDecoration(
                    labelText: 'السبب',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 2,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('إلغاء')),
            TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: TextButton.styleFrom(foregroundColor: AppColors.danger),
              child: const Text('إخلاء'),
            ),
          ],
        ),
      ),
    );

    if (result == true) {
      try {
        await _api.post('assets/$assetId/dispose', data: {
          'disposal_type': disposalType,
          'disposal_date':
              '${disposalDate.year}-${disposalDate.month.toString().padLeft(2, '0')}-${disposalDate.day.toString().padLeft(2, '0')}',
          'disposal_amount': double.tryParse(amountCtrl.text) ?? 0,
          'reason': reasonCtrl.text,
        });
        _showSuccess('تم إخلاء الأصل بنجاح');
        _loadAssets();
      } catch (e) {
        _showError('خطأ في إخلاء الأصل: ${ErrorUtils.sanitize(e)}');
      }
    }
  }

  // ── Filter Dialog ─────────────────────────────────────────────────────────

  void _showFilterDialog() {
    String? tempType = _filterType;
    String? tempStatus = _filterStatus;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('تصفية الأصول'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                value: tempType,
                decoration: const InputDecoration(
                  labelText: 'نوع الأصل',
                  border: OutlineInputBorder(),
                ),
                items: [
                  const DropdownMenuItem(value: null, child: Text('الكل')),
                  ..._assetTypeLabels.entries
                      .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))),
                ],
                onChanged: (v) => setDialogState(() => tempType = v),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: tempStatus,
                decoration: const InputDecoration(
                  labelText: 'الحالة',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: null, child: Text('الكل')),
                  DropdownMenuItem(value: 'active', child: Text('نشط')),
                  DropdownMenuItem(value: 'disposed', child: Text('تم التخلص')),
                ],
                onChanged: (v) => setDialogState(() => tempStatus = v),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(ctx);
                setState(() {
                  _filterType = null;
                  _filterStatus = null;
                });
                _loadAssets();
              },
              child: const Text('مسح الفلتر'),
              style: TextButton.styleFrom(foregroundColor: AppColors.textSecondary),
            ),
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('إلغاء'),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(ctx);
                setState(() {
                  _filterType = tempType;
                  _filterStatus = tempStatus;
                });
                _loadAssets();
              },
              child: const Text('تطبيق'),
            ),
          ],
        ),
      ),
    );
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الأصول الثابتة'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: Icon(
              _includeInactive ? Icons.visibility : Icons.visibility_off,
            ),
            onPressed: () {
              setState(() {
                _includeInactive = !_includeInactive;
              });
              _loadAssets();
            },
            tooltip: _includeInactive ? 'إخفاء غير النشطة' : 'عرض غير النشطة',
          ),
          IconButton(
            icon: const Icon(Icons.filter_alt),
            onPressed: _showFilterDialog,
            tooltip: 'تصفية',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadAssets,
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
                TextButton(onPressed: _loadAssets, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(child: _buildBody()),
        ],
      ),
      floatingActionButton: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          FloatingActionButton.extended(
            heroTag: 'depreciation',
            onPressed: _showRunDepreciationDialog,
            icon: const Icon(Icons.trending_down),
            label: const Text('تشغيل الإطفاء'),
          ),
          const SizedBox(height: 12),
          FloatingActionButton(
            heroTag: 'add',
            onPressed: _showCreateAssetDialog,
            tooltip: 'إضافة أصل جديد',
            child: const Icon(Icons.add),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const LoadingState();
    }

    if (_assets.isEmpty) {
      return const EmptyState(
        icon: Icons.apartment,
        title: 'لا توجد أصول',
        message: 'اضغط على + لإضافة أصل جديد',
      );
    }

    return RefreshIndicator(
      onRefresh: _loadAssets,
      child: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _assets.length,
              itemBuilder: (context, index) => _buildAssetCard(_assets[index]),
            ),
          ),
          if (_totalPages > 1)
            _buildPagination(),
        ],
      ),
    );
  }

  Widget _buildAssetCard(Map<String, dynamic> asset) {
    final status = asset['status'] ?? 'active';
    final isDisposed = status == 'disposed';

    return Padding(
      padding: const EdgeInsets.only(bottom: AppDimens.s2),
      child: AppCard(
        padding: EdgeInsets.zero,
        child: ListTile(
          leading: CircleAvatar(
            backgroundColor: isDisposed
                ? AppColors.warningContainer
                : AppColors.secondaryContainer,
            child: Icon(
              Icons.apartment,
              color: isDisposed ? AppColors.warning : AppColors.secondary,
            ),
          ),
          title: Row(
            children: [
              Expanded(
                child: Text(
                  '${asset['name'] ?? ''}',
                  style: AppTextStyles.titleSmall,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Chip(
                label: Text(
                  isDisposed ? 'تم التخلص' : 'نشط',
                  style: TextStyle(
                    fontSize: 10,
                    color: isDisposed ? AppColors.warning : AppColors.success,
                  ),
                ),
                backgroundColor: isDisposed
                    ? AppColors.warningContainer
                    : AppColors.successContainer,
                padding: EdgeInsets.zero,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ],
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('الكود: ${asset['code'] ?? ''}'),
              Row(
                children: [
                  Text('النوع: ${_assetTypeLabels[asset['asset_type']] ?? asset['asset_type'] ?? ''}'),
                  const SizedBox(width: 12),
                  Text('التكلفة: ${asset['cost'] ?? 0}'),
                ],
              ),
              if (asset['acquisition_date'] != null)
                Text('التاريخ: ${asset['acquisition_date']}'),
            ],
          ),
          trailing: PopupMenuButton(
            itemBuilder: (ctx) => [
              const PopupMenuItem(value: 'view', child: Text('عرض التفاصيل')),
              if (!isDisposed) ...[
                const PopupMenuItem(value: 'depreciation', child: Text('تسجيل إطفاء')),
                const PopupMenuItem(
                  value: 'dispose',
                  child: Text('إخلاء', style: TextStyle(color: AppColors.warning)),
                ),
              ],
            ],
            onSelected: (v) {
              if (v == 'view') {
                _viewAssetDetail(asset);
              } else if (v == 'depreciation') {
                _postDepreciation(asset['id']);
              } else if (v == 'dispose') {
                _disposeAsset(asset['id']);
              }
            },
          ),
        ),
      ),
    );
  }

  Widget _buildPagination() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            onPressed: _page > 1
                ? () {
                    setState(() => _page--);
                    _loadAssets();
                  }
                : null,
            icon: const Icon(Icons.chevron_left),
          ),
          Text('صفحة $_page من $_totalPages'),
          IconButton(
            onPressed: _page < _totalPages
                ? () {
                    setState(() => _page++);
                    _loadAssets();
                  }
                : null,
            icon: const Icon(Icons.chevron_right),
          ),
        ],
      ),
    );
  }
}
