import 'package:flutter/material.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../utils/error_utils.dart';
import '../../../utils/currency_helper.dart';
import '../../widgets/app_widgets.dart';

class InventoryScreen extends StatefulWidget {
  const InventoryScreen({super.key});

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('إدارة المخزون'),
        centerTitle: true,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'المخزون', icon: Icon(Icons.inventory_2)),
            Tab(text: 'الحركات', icon: Icon(Icons.swap_vert)),
            Tab(text: 'التحويلات', icon: Icon(Icons.swap_horiz)),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _StockTab(),
          _MovementsTab(),
          _TransfersTab(),
        ],
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab 1 – Stock
// ═════════════════════════════════════════════════════════════════════════════

class _StockTab extends StatefulWidget {
  @override
  State<_StockTab> createState() => _StockTabState();
}

class _StockTabState extends State<_StockTab> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _movements = [];
  bool _isLoading = true;
  String? _error;
  String _searchText = '';
  bool _lowStockOnly = false;
  Map<String, dynamic>? _valuation;

  @override
  void initState() {
    super.initState();
    _loadStock();
  }

  Future<void> _loadStock() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get(
        'inventory/low-stock',
        queryParameters: {
          if (_searchText.isNotEmpty) 'search': _searchText,
        },
      );
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _movements = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _loadValuation(String entityType, String entityId) async {
    try {
      final today = DateTime.now();
      final response = await _api.get('inventory/$entityType/$entityId/valuation',
          queryParameters: {
            'as_of_date':
                '${today.year}-${today.month.toString().padLeft(2, '0')}-${today.day.toString().padLeft(2, '0')}',
            'method': 'fifo',
          });
      final data = response['data'] ?? response;
      if (!mounted) return;
      showModalBottomSheet(
        context: context,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        builder: (ctx) => Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'تقييم المخزون (FIFO)',
                style: AppTextStyles.headlineSmall,
              ),
              const Divider(),
              if (data is Map) ...[
                _valuationRow('إجمالي الكمية', '${data['total_quantity'] ?? '-'}'),
                _valuationRow('إجمالي القيمة', '${data['total_cost'] ?? '-'}'),
                _valuationRow('متوسط تكلفة الوحدة', '${data['average_cost'] ?? '-'}'),
                _valuationRow('العملة', '${data['currency'] ?? '-'}'),
                _valuationRow('الطريقة', '${data['valuation_method'] ?? '-'}'),
                if (data['batches'] != null && data['batches'] is List) ...[
                  const SizedBox(height: 12),
                  const Text('الدفعات:', style: AppTextStyles.titleSmall),
                  ...((data['batches'] as List).map((b) => ListTile(
                        dense: true,
                        title: Text('دفعة: ${b['batch_number'] ?? ''}'),
                        subtitle: Text('الكمية: ${b['current_quantity'] ?? b['quantity'] ?? 0} | التكلفة: ${b['unit_cost'] ?? 0}'),
                      ))),
                ],
              ],
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: AppButton(
                  onPressed: () => Navigator.pop(ctx),
                  label: 'إغلاق',
                  variant: AppButtonVariant.primary,
                  expanded: true,
                ),
              ),
            ],
          ),
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ErrorUtils.sanitize(e)),
          backgroundColor: AppColors.danger,
        ),
      );
    }
  }

  Widget _valuationRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          Text(value, style: AppTextStyles.titleSmall),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        if (_error != null)
          MaterialBanner(
            content: Text(ErrorUtils.sanitize(_error)),
            leading: const Icon(Icons.wifi_off, color: AppColors.warning),
            actions: [
              TextButton(onPressed: _loadStock, child: const Text('إعادة المحاولة')),
            ],
            backgroundColor: AppColors.warningContainer,
          ),
        // Search bar
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    hintText: 'بحث...',
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(AppDimens.radiusInput),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12),
                  ),
                  onChanged: (v) => _searchText = v,
                  onSubmitted: (_) => _loadStock(),
                ),
              ),
              const SizedBox(width: 8),
              FilterChip(
                label: const Text('مخزون منخفض'),
                selected: _lowStockOnly,
                onSelected: (v) {
                  setState(() => _lowStockOnly = v);
                  _loadStock();
                },
                selectedColor: AppColors.warningContainer,
              ),
              const SizedBox(width: 4),
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _loadStock,
              ),
            ],
          ),
        ),
        // Content
        Expanded(child: _buildBody()),
      ],
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());

    if (_movements.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.inventory_2, size: 64, color: Theme.of(context).colorScheme.onSurfaceVariant),
            const SizedBox(height: 16),
            Text(
              'لا توجد بيانات مخزون',
              style: AppTextStyles.headlineSmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadStock,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        itemCount: _movements.length,
        itemBuilder: (context, index) {
          final item = _movements[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: AppDimens.s2),
            child: AppCard(
              padding: EdgeInsets.zero,
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: AppColors.secondaryContainer,
                  child: const Icon(Icons.inventory_2, color: AppColors.secondary),
                ),
                title: Text(
                  '${item['name'] ?? item['product_name'] ?? ''}',
                  style: AppTextStyles.titleSmall,
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('الكمية: ${item['quantity'] ?? item['stock_quantity'] ?? 0}'),
                    if (item['unit_cost'] != null)
                      Text('تكلفة الوحدة: ${item['unit_cost']}'),
                    if (item['location'] != null)
                      Text('الموقع: ${item['location']}'),
                  ],
                ),
                trailing: PopupMenuButton(
                  itemBuilder: (ctx) => [
                    const PopupMenuItem(value: 'valuation', child: Text('تقييم المخزون')),
                    const PopupMenuItem(value: 'movements', child: Text('الحركات')),
                    const PopupMenuItem(value: 'batch', child: Text('إضافة دفعة')),
                    const PopupMenuItem(value: 'consume', child: Text('استهلاك دفعة')),
                  ],
                  onSelected: (v) {
                    if (v == 'valuation') {
                      _loadValuation(
                        item['entity_type'] ?? 'product',
                        item['entity_id'] ?? item['id'] ?? '',
                      );
                    } else if (v == 'movements') {
                      _showItemMovements(
                        item['entity_type'] ?? 'product',
                        item['entity_id'] ?? item['id'] ?? '',
                      );
                    } else if (v == 'batch') {
                      _showCreateBatchDialog(
                        item['entity_type'] ?? 'product',
                        item['entity_id'] ?? item['id'] ?? '',
                      );
                    } else if (v == 'consume') {
                      _showConsumeBatchDialog(
                        item['entity_type'] ?? 'product',
                        item['entity_id'] ?? item['id'] ?? '',
                      );
                    }
                  },
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Future<void> _showItemMovements(String entityType, String entityId) async {
    try {
      final response = await _api.get('inventory/$entityType/$entityId/movements');
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      final movements = (items as List).cast<Map<String, dynamic>>();
      if (!mounted) return;
      showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        builder: (ctx) => DraggableScrollableSheet(
          initialChildSize: 0.6,
          maxChildSize: 0.9,
          expand: false,
          builder: (ctx, scrollCtrl) => ListView(
            controller: scrollCtrl,
            padding: const EdgeInsets.all(16),
            children: [
              Center(
                child: Container(
                  width: 40, height: 4,
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const Text(
                'حركات المخزون',
                style: AppTextStyles.headlineSmall,
              ),
              const Divider(),
              if (movements.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: Text('لا توجد حركات')),
                )
              else
                ...movements.map((m) => ListTile(
                      leading: Icon(
                        _movementIcon(m['movement_type']),
                        color: _movementColor(m['movement_type']),
                      ),
                      title: Text('${m['movement_type'] ?? ''}'),
                      subtitle: Text(
                        'الكمية: ${m['quantity'] ?? 0} | التاريخ: ${m['created_at'] ?? ''}',
                      ),
                      trailing: m['unit_cost'] != null
                          ? Text('${m['unit_cost']}', style: AppTextStyles.moneyMedium)
                          : null,
                    )),
            ],
          ),
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ErrorUtils.sanitize(e)),
          backgroundColor: AppColors.danger,
        ),
      );
    }
  }

  Future<void> _showCreateBatchDialog(String entityType, String entityId) async {
    final batchNumCtrl = TextEditingController();
    final qtyCtrl = TextEditingController();
    final costCtrl = TextEditingController(text: '0');
    final locationCtrl = TextEditingController();
    DateTime? productionDate;
    DateTime? expiryDate;

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
            left: 16, right: 16, top: 16,
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'إضافة دفعة جديدة',
                  style: AppTextStyles.headlineSmall,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: batchNumCtrl,
                  decoration: const InputDecoration(
                    labelText: 'رقم الدفعة *',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.numbers),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: qtyCtrl,
                  decoration: const InputDecoration(
                    labelText: 'الكمية *',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.inventory),
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: costCtrl,
                  decoration: const InputDecoration(
                    labelText: 'تكلفة الوحدة *',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.attach_money),
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 12),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('تاريخ الإنتاج'),
                  subtitle: Text(
                    productionDate != null
                        ? '${productionDate!.year}-${productionDate!.month.toString().padLeft(2, '0')}-${productionDate!.day.toString().padLeft(2, '0')}'
                        : 'لم يتم التحديد',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (picked != null) setSheetState(() => productionDate = picked);
                  },
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('تاريخ الانتهاء'),
                  subtitle: Text(
                    expiryDate != null
                        ? '${expiryDate!.year}-${expiryDate!.month.toString().padLeft(2, '0')}-${expiryDate!.day.toString().padLeft(2, '0')}'
                        : 'لم يتم التحديد',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: DateTime.now().add(const Duration(days: 365)),
                      firstDate: DateTime.now(),
                      lastDate: DateTime(2040),
                    );
                    if (picked != null) setSheetState(() => expiryDate = picked);
                  },
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
                          if (batchNumCtrl.text.isEmpty || qtyCtrl.text.isEmpty) {
                            ScaffoldMessenger.of(ctx).showSnackBar(
                              const SnackBar(content: Text('يرجى ملء الحقول المطلوبة')),
                            );
                            return;
                          }
                          Navigator.pop(ctx, true);
                          _createBatch(
                            entityType: entityType,
                            entityId: entityId,
                            batchNumber: batchNumCtrl.text,
                            quantity: int.tryParse(qtyCtrl.text) ?? 0,
                            unitCost: double.tryParse(costCtrl.text) ?? 0,
                            productionDate: productionDate,
                            expiryDate: expiryDate,
                            location: locationCtrl.text.isNotEmpty ? locationCtrl.text : null,
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

  Future<void> _createBatch({
    required String entityType,
    required String entityId,
    required String batchNumber,
    required int quantity,
    double? unitCost,
    DateTime? productionDate,
    DateTime? expiryDate,
    String? location,
  }) async {
    try {
      await _api.post('inventory/batches', data: {
        'entity_type': entityType,
        'entity_id': entityId,
        'batch_number': batchNumber,
        'quantity': quantity,
        'unit_cost': unitCost ?? 0,
        'currency': CurrencyHelper.baseCurrency,
        if (productionDate != null)
          'production_date':
              '${productionDate.year}-${productionDate.month.toString().padLeft(2, '0')}-${productionDate.day.toString().padLeft(2, '0')}',
        if (expiryDate != null)
          'expiry_date':
              '${expiryDate.year}-${expiryDate.month.toString().padLeft(2, '0')}-${expiryDate.day.toString().padLeft(2, '0')}',
        if (location != null) 'location': location,
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('تم إضافة الدفعة بنجاح'),
          backgroundColor: AppColors.success,
        ),
      );
      _loadStock();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
      );
    }
  }

  void _showConsumeBatchDialog(String entityType, String entityId) {
    final batchIdCtrl = TextEditingController();
    final qtyCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
          left: 16, right: 16, top: 16,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'استهلاك دفعة',
                style: AppTextStyles.headlineSmall,
              ),
              const SizedBox(height: 12),
              Text(
                'الكيان: $entityType ($entityId)',
                style: const TextStyle(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: batchIdCtrl,
                decoration: const InputDecoration(
                  labelText: 'معرف الدفعة (batch id) *',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: qtyCtrl,
                decoration: const InputDecoration(
                  labelText: 'الكمية المطلوب استهلاكها *',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: AppButton(
                      onPressed: () => Navigator.pop(ctx),
                      label: 'إلغاء',
                      variant: AppButtonVariant.cancel,
                      expanded: true,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: AppButton(
                      onPressed: () async {
                        final batchId = batchIdCtrl.text.trim();
                        final qty = int.tryParse(qtyCtrl.text.trim());
                        if (batchId.isEmpty || qty == null || qty <= 0) {
                          ScaffoldMessenger.of(ctx).showSnackBar(
                            const SnackBar(content: Text('أدخل معرف الدفعة والكمية')),
                          );
                          return;
                        }
                        Navigator.pop(ctx);
                        try {
                          await _api.post(
                              'inventory/batches/$batchId/consume',
                              data: {
                                'quantity': qty,
                                'reference_type': 'manual',
                                'reference_id': '',
                              });
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('تم استهلاك الدفعة بنجاح'),
                              backgroundColor: AppColors.success,
                            ),
                          );
                          _loadStock();
                        } catch (e) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(ErrorUtils.sanitize(e)),
                              backgroundColor: AppColors.danger,
                            ),
                          );
                        }
                      },
                      label: 'استهلاك',
                      variant: AppButtonVariant.danger,
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
    );
  }

  IconData _movementIcon(String? type) {
    switch (type) {
      case 'purchase':
        return Icons.add_shopping_cart;
      case 'sale':
        return Icons.shopping_cart;
      case 'adjustment':
        return Icons.tune;
      case 'transfer':
        return Icons.swap_horiz;
      default:
        return Icons.swap_vert;
    }
  }

  Color _movementColor(String? type) {
    switch (type) {
      case 'purchase':
        return AppColors.success;
      case 'sale':
        return AppColors.secondary;
      case 'adjustment':
        return AppColors.warning;
      case 'transfer':
        return AppColors.primary;
      default:
        return AppColors.textSecondary;
    }
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab 2 – Movements
// ═════════════════════════════════════════════════════════════════════════════

class _MovementsTab extends StatefulWidget {
  @override
  State<_MovementsTab> createState() => _MovementsTabState();
}

class _MovementsTabState extends State<_MovementsTab>
    with SingleTickerProviderStateMixin {
  final ApiService _api = ApiService();
  late TabController _movementTabCtrl;
  List<Map<String, dynamic>> _recentMovements = [];
  bool _isLoading = true;

  final _movEntityTypeCtrl = TextEditingController(text: 'product');
  final _movEntityIdCtrl = TextEditingController();
  final _movQtyCtrl = TextEditingController();
  final _movCostCtrl = TextEditingController();
  final _movRefTypeCtrl = TextEditingController();
  final _movRefIdCtrl = TextEditingController();
  final _movBatchCtrl = TextEditingController();
  final _movSerialCtrl = TextEditingController();
  final _movLocationCtrl = TextEditingController();

  final _adjEntityTypeCtrl = TextEditingController(text: 'product');
  final _adjEntityIdCtrl = TextEditingController();
  final _adjOldQtyCtrl = TextEditingController();
  final _adjNewQtyCtrl = TextEditingController();
  final _adjReasonCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _movementTabCtrl = TabController(length: 4, vsync: this);
    _loadRecentMovements();
  }

  @override
  void dispose() {
    _movementTabCtrl.dispose();
    _movEntityTypeCtrl.dispose();
    _movEntityIdCtrl.dispose();
    _movQtyCtrl.dispose();
    _movCostCtrl.dispose();
    _movRefTypeCtrl.dispose();
    _movRefIdCtrl.dispose();
    _movBatchCtrl.dispose();
    _movSerialCtrl.dispose();
    _movLocationCtrl.dispose();
    _adjEntityTypeCtrl.dispose();
    _adjEntityIdCtrl.dispose();
    _adjOldQtyCtrl.dispose();
    _adjNewQtyCtrl.dispose();
    _adjReasonCtrl.dispose();
    super.dispose();
  }

  void _resetMovementControllers() {
    _movEntityTypeCtrl.text = 'product';
    _movEntityIdCtrl.clear();
    _movQtyCtrl.clear();
    _movCostCtrl.clear();
    _movRefTypeCtrl.clear();
    _movRefIdCtrl.clear();
    _movBatchCtrl.clear();
    _movSerialCtrl.clear();
    _movLocationCtrl.clear();
  }

  void _resetAdjustmentControllers() {
    _adjEntityTypeCtrl.text = 'product';
    _adjEntityIdCtrl.clear();
    _adjOldQtyCtrl.clear();
    _adjNewQtyCtrl.clear();
    _adjReasonCtrl.clear();
  }

  Future<void> _loadRecentMovements() async {
    setState(() => _isLoading = true);
    try {
      final response = await _api.get('inventory/movements', queryParameters: {'limit': 50});
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _recentMovements = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Sub-tabs for movement types
        TabBar(
          controller: _movementTabCtrl,
          isScrollable: true,
          tabs: const [
            Tab(text: 'عامة'),
            Tab(text: 'شراء'),
            Tab(text: 'بيع'),
            Tab(text: 'تعديل'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _movementTabCtrl,
            children: [
              _buildMovementForm('general'),
              _buildMovementForm('purchase'),
              _buildMovementForm('sale'),
              _buildAdjustmentForm(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMovementForm(String type) {
    _resetMovementControllers();
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            type == 'purchase'
                ? 'حركة شراء'
                : type == 'sale'
                    ? 'حركة بيع'
                    : 'حركة عامة',
            style: AppTextStyles.titleMedium,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _movEntityTypeCtrl,
            decoration: const InputDecoration(
              labelText: 'نوع الكيان (product/variant)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _movEntityIdCtrl,
            decoration: const InputDecoration(
              labelText: 'معرف الكيان *',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _movQtyCtrl,
            decoration: const InputDecoration(
              labelText: 'الكمية *',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _movCostCtrl,
            decoration: const InputDecoration(
              labelText: 'تكلفة الوحدة',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.number,
          ),
          if (type == 'general') ...[
            const SizedBox(height: 12),
            TextField(
              controller: _movRefTypeCtrl,
              decoration: const InputDecoration(
                labelText: 'نوع المرجع',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _movRefIdCtrl,
              decoration: const InputDecoration(
                labelText: 'معرف المرجع',
                border: OutlineInputBorder(),
              ),
            ),
          ],
          const SizedBox(height: 12),
          TextField(
            controller: _movBatchCtrl,
            decoration: const InputDecoration(
              labelText: 'رقم الدفعة',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _movSerialCtrl,
            decoration: const InputDecoration(
              labelText: 'الرقم التسلسلي',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _movLocationCtrl,
            decoration: const InputDecoration(
              labelText: 'الموقع',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          AppButton(
            onPressed: () async {
              if (_movEntityIdCtrl.text.isEmpty || _movQtyCtrl.text.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('يرجى ملء الحقول المطلوبة')),
                );
                return;
              }
              try {
                final endpoint = type == 'purchase'
                    ? 'inventory/movements/purchase'
                    : type == 'sale'
                        ? 'inventory/movements/sale'
                        : 'inventory/movements';
                await _api.post(endpoint, data: {
                  'entity_type': _movEntityTypeCtrl.text,
                  'entity_id': _movEntityIdCtrl.text,
                  'movement_type': type == 'general' ? 'adjustment' : type,
                  'quantity': int.tryParse(_movQtyCtrl.text) ?? 0,
                  if (_movCostCtrl.text.isNotEmpty)
                    'unit_cost': double.tryParse(_movCostCtrl.text),
                  if (type == 'general' && _movRefTypeCtrl.text.isNotEmpty)
                    'reference_type': _movRefTypeCtrl.text,
                  if (type == 'general' && _movRefIdCtrl.text.isNotEmpty)
                    'reference_id': _movRefIdCtrl.text,
                  if (_movBatchCtrl.text.isNotEmpty) 'batch_number': _movBatchCtrl.text,
                  if (_movSerialCtrl.text.isNotEmpty) 'serial_number': _movSerialCtrl.text,
                  if (_movLocationCtrl.text.isNotEmpty) 'location': _movLocationCtrl.text,
                });
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('تم إنشاء الحركة بنجاح'),
                    backgroundColor: AppColors.success,
                  ),
                );
                _loadRecentMovements();
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(ErrorUtils.sanitize(e)),
                    backgroundColor: AppColors.danger,
                  ),
                );
              }
            },
            icon: Icons.send,
            label: 'إرسال الحركة',
            variant: AppButtonVariant.primary,
            expanded: true,
          ),
          const SizedBox(height: 24),
          // Recent movements list
          const Text(
            'آخر الحركات',
            style: AppTextStyles.titleMedium,
          ),
          const SizedBox(height: 8),
          if (_isLoading)
            const Center(child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(),
            ))
          else if (_recentMovements.isEmpty)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: Text('لا توجد حركات')),
            )
          else
            ..._recentMovements.map((m) => Padding(
                  padding: const EdgeInsets.only(bottom: AppDimens.s2),
                  child: AppCard(
                    padding: EdgeInsets.zero,
                    child: ListTile(
                      dense: true,
                      leading: Icon(
                        _movementIcon(m['movement_type']),
                        color: _movementColor(m['movement_type']),
                      ),
                      title: Text('${m['movement_type'] ?? ''} - ${m['entity_id'] ?? ''}'),
                      subtitle: Text(
                        'الكمية: ${m['quantity'] ?? 0} | ${m['created_at'] ?? ''}',
                      ),
                      trailing: m['unit_cost'] != null
                          ? Text('${m['unit_cost']}', style: AppTextStyles.moneyMedium)
                          : null,
                    ),
                  ),
                )),
        ],
      ),
    );
  }

  Widget _buildAdjustmentForm() {
    _resetAdjustmentControllers();
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'تعديل المخزون',
            style: AppTextStyles.titleMedium,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _adjEntityTypeCtrl,
            decoration: const InputDecoration(
              labelText: 'نوع الكيان',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _adjEntityIdCtrl,
            decoration: const InputDecoration(
              labelText: 'معرف الكيان *',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _adjOldQtyCtrl,
            decoration: const InputDecoration(
              labelText: 'الكمية الحالية *',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _adjNewQtyCtrl,
            decoration: const InputDecoration(
              labelText: 'الكمية الجديدة *',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _adjReasonCtrl,
            decoration: const InputDecoration(
              labelText: 'سبب التعديل *',
              border: OutlineInputBorder(),
            ),
            maxLines: 2,
          ),
          const SizedBox(height: 16),
          AppButton(
            onPressed: () async {
              if (_adjEntityIdCtrl.text.isEmpty ||
                  _adjOldQtyCtrl.text.isEmpty ||
                  _adjNewQtyCtrl.text.isEmpty ||
                  _adjReasonCtrl.text.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('يرجى ملء جميع الحقول المطلوبة')),
                );
                return;
              }
              try {
                await _api.post('inventory/movements/adjustment', data: {
                  'entity_type': _adjEntityTypeCtrl.text,
                  'entity_id': _adjEntityIdCtrl.text,
                  'old_quantity': int.tryParse(_adjOldQtyCtrl.text) ?? 0,
                  'new_quantity': int.tryParse(_adjNewQtyCtrl.text) ?? 0,
                  'reason': _adjReasonCtrl.text,
                });
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('تم تعديل المخزون بنجاح'),
                    backgroundColor: AppColors.success,
                  ),
                );
                _loadRecentMovements();
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(ErrorUtils.sanitize(e)),
                    backgroundColor: AppColors.danger,
                  ),
                );
              }
            },
            icon: Icons.tune,
            label: 'تطبيق التعديل',
            variant: AppButtonVariant.primary,
            expanded: true,
          ),
          const SizedBox(height: 24),
          const Text(
            'آخر الحركات',
            style: AppTextStyles.titleMedium,
          ),
          const SizedBox(height: 8),
          if (_isLoading)
            const Center(child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(),
            ))
          else if (_recentMovements.isEmpty)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: Text('لا توجد حركات')),
            )
          else
            ..._recentMovements.map((m) => Padding(
                  padding: const EdgeInsets.only(bottom: AppDimens.s2),
                  child: AppCard(
                    padding: EdgeInsets.zero,
                    child: ListTile(
                      dense: true,
                      leading: Icon(
                        _movementIcon(m['movement_type']),
                        color: _movementColor(m['movement_type']),
                      ),
                      title: Text('${m['movement_type'] ?? ''} - ${m['entity_id'] ?? ''}'),
                      subtitle: Text(
                        'الكمية: ${m['quantity'] ?? 0} | ${m['created_at'] ?? ''}',
                      ),
                    ),
                  ),
                )),
        ],
      ),
    );
  }

  IconData _movementIcon(String? type) {
    switch (type) {
      case 'purchase':
        return Icons.add_shopping_cart;
      case 'sale':
        return Icons.shopping_cart;
      case 'adjustment':
        return Icons.tune;
      case 'transfer':
        return Icons.swap_horiz;
      default:
        return Icons.swap_vert;
    }
  }

  Color _movementColor(String? type) {
    switch (type) {
      case 'purchase':
        return AppColors.success;
      case 'sale':
        return AppColors.secondary;
      case 'adjustment':
        return AppColors.warning;
      case 'transfer':
        return AppColors.primary;
      default:
        return AppColors.textSecondary;
    }
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab 3 – Transfers
// ═════════════════════════════════════════════════════════════════════════════

class _TransfersTab extends StatefulWidget {
  @override
  State<_TransfersTab> createState() => _TransfersTabState();
}

class _TransfersTabState extends State<_TransfersTab> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _transfers = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTransfers();
  }

  Future<void> _loadTransfers() async {
    setState(() => _isLoading = true);
    try {
      final response = await _api.get('inventory/transfers');
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _transfers = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _createTransfer({
    required String entityType,
    required String entityId,
    required int quantity,
    double? unitCost,
    required String fromLocation,
    required String toLocation,
    String? batchNumber,
  }) async {
    try {
      final response = await _api.post('inventory/transfers', data: {
        'entity_type': entityType,
        'entity_id': entityId,
        'quantity': quantity,
        'unit_cost': unitCost ?? 0,
        'from_location': fromLocation,
        'to_location': toLocation,
        if (batchNumber != null) 'batch_number': batchNumber,
      });
      final transferData = response['data'] ?? response;
      final transferId = transferData['id'] ?? transferData['transfer_id'];
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('تم إنشاء التحويل بنجاح'),
          backgroundColor: AppColors.success,
        ),
      );
      _loadTransfers();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
      );
    }
  }

  Future<void> _completeTransfer(String transferId) async {
    try {
      await _api.post('inventory/transfers/$transferId/complete');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('تم إكمال التحويل بنجاح'),
          backgroundColor: AppColors.success,
        ),
      );
      _loadTransfers();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
      );
    }
  }

  void _showCreateTransferDialog() {
    final entityTypeCtrl = TextEditingController(text: 'product');
    final entityIdCtrl = TextEditingController();
    final qtyCtrl = TextEditingController();
    final costCtrl = TextEditingController(text: '0');
    final fromLocationCtrl = TextEditingController();
    final toLocationCtrl = TextEditingController();
    final batchCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
          left: 16, right: 16, top: 16,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'تحويل مخزون',
                style: AppTextStyles.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: entityTypeCtrl,
                      decoration: const InputDecoration(
                        labelText: 'نوع الكيان',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: entityIdCtrl,
                      decoration: const InputDecoration(
                        labelText: 'معرف الكيان *',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: qtyCtrl,
                      decoration: const InputDecoration(
                        labelText: 'الكمية *',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: costCtrl,
                      decoration: const InputDecoration(
                        labelText: 'تكلفة الوحدة *',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: fromLocationCtrl,
                      decoration: const InputDecoration(
                        labelText: 'من الموقع *',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: toLocationCtrl,
                      decoration: const InputDecoration(
                        labelText: 'إلى الموقع *',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: batchCtrl,
                decoration: const InputDecoration(
                  labelText: 'رقم الدفعة (اختياري)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: AppButton(
                      onPressed: () => Navigator.pop(ctx),
                      label: 'إلغاء',
                      variant: AppButtonVariant.cancel,
                      expanded: true,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: AppButton(
                      onPressed: () {
                        if (entityIdCtrl.text.isEmpty ||
                            qtyCtrl.text.isEmpty ||
                            fromLocationCtrl.text.isEmpty ||
                            toLocationCtrl.text.isEmpty) {
                          ScaffoldMessenger.of(ctx).showSnackBar(
                            const SnackBar(content: Text('يرجى ملء الحقول المطلوبة')),
                          );
                          return;
                        }
                        Navigator.pop(ctx);
                        _createTransfer(
                          entityType: entityTypeCtrl.text,
                          entityId: entityIdCtrl.text,
                          quantity: int.tryParse(qtyCtrl.text) ?? 0,
                          unitCost: double.tryParse(costCtrl.text),
                          fromLocation: fromLocationCtrl.text.trim(),
                          toLocation: toLocationCtrl.text.trim(),
                          batchNumber: batchCtrl.text.trim().isEmpty
                              ? null
                              : batchCtrl.text.trim(),
                        );
                      },
                      label: 'إنشاء التحويل',
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
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              const Expanded(
                child: Text(
                  'التحويلات',
                  style: AppTextStyles.titleMedium,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _loadTransfers,
              ),
            ],
          ),
        ),
        // Transfers list
        Expanded(
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _transfers.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.swap_horiz, size: 64, color: AppColors.textMuted),
                          const SizedBox(height: 16),
                          Text(
                            'لا توجد تحويلات',
                            style: AppTextStyles.headlineSmall.copyWith(
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _loadTransfers,
                      child: ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        itemCount: _transfers.length,
                        itemBuilder: (context, index) {
                          final transfer = _transfers[index];
                          final status = transfer['status'] ?? 'pending';
                          return Padding(
                            padding: const EdgeInsets.only(bottom: AppDimens.s2),
                            child: AppCard(
                              padding: EdgeInsets.zero,
                              child: ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: status == 'completed'
                                      ? AppColors.successContainer
                                      : AppColors.warningContainer,
                                  child: Icon(
                                    Icons.swap_horiz,
                                    color: status == 'completed'
                                        ? AppColors.success
                                        : AppColors.warning,
                                  ),
                                ),
                                title: Text(
                                  '${transfer['from_location'] ?? transfer['from_entity_id'] ?? '؟'} → ${transfer['to_location'] ?? transfer['to_entity_id'] ?? '؟'}',
                                  style: AppTextStyles.titleSmall,
                                ),
                                subtitle: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('الكيان: ${transfer['entity_id'] ?? ''} | الكمية: ${transfer['quantity'] ?? 0}'),
                                    if (transfer['unit_cost'] != null)
                                      Text('تكلفة الوحدة: ${transfer['unit_cost']}'),
                                    Text('الحالة: ${status == 'completed' ? 'مكتمل' : 'قيد الانتظار'}'),
                                  ],
                                ),
                                trailing: status != 'completed'
                                    ? IconButton(
                                        icon: const Icon(Icons.check_circle, color: AppColors.success),
                                        onPressed: () {
                                          _showConfirmComplete(transfer['id']);
                                        },
                                        tooltip: 'إكمال التحويل',
                                      )
                                    : const Icon(Icons.check, color: AppColors.success),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
        ),
        // FAB
        Padding(
          padding: const EdgeInsets.all(12),
          child: SizedBox(
            width: double.infinity,
            child: FloatingActionButton.extended(
              onPressed: _showCreateTransferDialog,
              icon: const Icon(Icons.add),
              label: const Text('تحويل جديد'),
            ),
          ),
        ),
      ],
    );
  }

  void _showConfirmComplete(String transferId) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('إكمال التحويل'),
        content: const Text('هل أنت متأكد من إكمال هذا التحويل؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('إلغاء')),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              _completeTransfer(transferId);
            },
            child: const Text('إكمال'),
          ),
        ],
      ),
    );
  }
}
