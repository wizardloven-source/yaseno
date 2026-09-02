import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import 'package:intl/intl.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';
import '../../../presentation/widgets/app_widgets.dart';

class FiscalPeriodsScreen extends StatefulWidget {
  const FiscalPeriodsScreen({super.key});

  @override
  State<FiscalPeriodsScreen> createState() => _FiscalPeriodsScreenState();
}

class _FiscalPeriodsScreenState extends State<FiscalPeriodsScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _periods = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPeriods();
  }

  Future<void> _loadPeriods() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _api.get('fiscal-periods');
      final data = response['data'] ?? response;
      final items = (data is Map ? data['items'] : data) ?? [];
      setState(() {
        _periods = (items as List).cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _closePeriod(String id) async {
    try {
      await _api.post('fiscal-periods/$id/close');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم إغلاق الفترة بنجاح'), backgroundColor: AppColors.success),
        );
        _loadPeriods();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  Future<void> _reopenPeriod(String id) async {
    try {
      await _api.post('fiscal-periods/$id/reopen');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم إعادة فتح الفترة بنجاح'), backgroundColor: AppColors.success),
        );
        _loadPeriods();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  Future<void> _closeYear(String id) async {
    final controller = TextEditingController();
    final code = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('الإقفال السنوي'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('يرجى إدخال رمز حساب الأرباح المرحلة.'),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'رمز حساب الأرباح المرحلة',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إلغاء'),
          ),
          AppButton(
            label: 'إقفال',
            variant: AppButtonVariant.success,
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
          ),
        ],
      ),
    );
    controller.dispose();
    if (code == null || code.isEmpty) return;

    try {
      await _api.post('fiscal-periods/$id/close-year', data: {
        'retained_earnings_code': code,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم الإقفال السنوي بنجاح'), backgroundColor: AppColors.success),
        );
        _loadPeriods();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
      }
    }
  }

  void _showCreateDialog() {
    final nameController = TextEditingController();
    DateTime? startDate;
    DateTime? endDate;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('إضافة فترة مالية جديدة'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(
                    labelText: 'اسم الفترة',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                ListTile(
                  title: Text(
                    startDate != null
                        ? 'من: ${DateFormat('yyyy-MM-dd').format(startDate!)}'
                        : 'تاريخ البداية',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  shape: RoundedRectangleBorder(
                    side: BorderSide(color: AppColors.outline),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime(2030),
                    );
                    if (picked != null) setDialogState(() => startDate = picked);
                  },
                ),
                const SizedBox(height: 12),
                ListTile(
                  title: Text(
                    endDate != null
                        ? 'إلى: ${DateFormat('yyyy-MM-dd').format(endDate!)}'
                        : 'تاريخ النهاية',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  shape: RoundedRectangleBorder(
                    side: BorderSide(color: AppColors.outline),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: ctx,
                      initialDate: DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime(2035),
                    );
                    if (picked != null) setDialogState(() => endDate = picked);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('إلغاء'),
            ),
            AppButton(
              label: 'حفظ',
              variant: AppButtonVariant.success,
              onPressed: () async {
                if (nameController.text.trim().isEmpty ||
                    startDate == null ||
                    endDate == null) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    const SnackBar(content: Text('يرجى ملء جميع الحقول')),
                  );
                  return;
                }
                Navigator.pop(ctx);
                try {
                  await _api.post('fiscal-periods', data: {
                    'name': nameController.text.trim(),
                    'start_date': DateFormat('yyyy-MM-dd').format(startDate!),
                    'end_date': DateFormat('yyyy-MM-dd').format(endDate!),
                  });
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('تم إنشاء الفترة بنجاح'), backgroundColor: AppColors.success),
                    );
                    _loadPeriods();
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger));
                  }
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الفترات المالية'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadPeriods,
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
                TextButton(onPressed: _loadPeriods, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(child: _buildBody()),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showCreateDialog,
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_periods.isEmpty) return const Center(child: Text('لا توجد فترات مالية'));
    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: _periods.length,
      itemBuilder: (context, index) {
        final p = _periods[index];
        final bool isOpen = (p['status'] ?? '').toString().toLowerCase() == 'open';
        final id = p['id'] ?? '';
        return Card(
          margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: isOpen ? AppColors.success.withOpacity(0.15) : AppColors.danger.withOpacity(0.15),
              child: Icon(
                Icons.circle,
                size: 14,
                color: isOpen ? AppColors.success : AppColors.danger,
              ),
            ),
            title: Text(p['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text(
              '${DateFormat('yyyy-MM-dd').format(DateTime.parse(p['start_date']))} - ${DateFormat('yyyy-MM-dd').format(DateTime.parse(p['end_date']))}',
              style: const TextStyle(fontSize: 12),
            ),
            trailing: PopupMenuButton<String>(
              onSelected: (value) {
                if (value == 'close') _closePeriod(id.toString());
                if (value == 'reopen') _reopenPeriod(id.toString());
                if (value == 'close_year') _closeYear(id.toString());
              },
              itemBuilder: (ctx) => [
                if (isOpen)
                  const PopupMenuItem(value: 'close', child: Text('إغلاق')),
                if (isOpen)
                  const PopupMenuItem(value: 'close_year', child: Text('إقفال سنوي')),
                if (!isOpen)
                  const PopupMenuItem(value: 'reopen', child: Text('إعادة الفتح')),
              ],
            ),
          ),
        );
      },
    );
  }
}
