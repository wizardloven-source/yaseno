import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import 'package:intl/intl.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});

  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  final ApiService _api = ApiService();
  final ScrollController _scrollController = ScrollController();

  List<Map<String, dynamic>> _logs = [];
  bool _isLoading = true;
  bool _isLoadingMore = false;
  String? _error;
  int _currentPage = 1;
  bool _hasMore = true;
  int _totalCount = 0;

  String? _filterEntityType;
  String? _filterAction;
  DateTime? _dateFrom;
  DateTime? _dateTo;

  final List<String> _entityTypes = [
    'invoice',
    'payment',
    'purchase_order',
    'journal_entry',
    'expense',
    'workflow',
    'user',
    'settings',
  ];

  final List<String> _actions = [
    'create',
    'update',
    'delete',
    'approve',
    'reject',
    'post',
    'cancel',
    'login',
    'logout',
  ];

  @override
  void initState() {
    super.initState();
    _loadLogs(reset: true);
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
            _scrollController.position.maxScrollExtent - 200 &&
        !_isLoadingMore &&
        _hasMore) {
      _loadLogs(reset: false);
    }
  }

  Future<void> _loadLogs({required bool reset}) async {
    if (reset) {
      setState(() {
        _isLoading = true;
        _error = null;
        _currentPage = 1;
        _hasMore = true;
        _logs = [];
      });
    } else {
      setState(() => _isLoadingMore = true);
    }

    try {
      final params = <String, dynamic>{
        'page': _currentPage,
        'limit': 50,
      };
      if (_filterEntityType != null) params['entity_type'] = _filterEntityType;
      if (_filterAction != null) params['action'] = _filterAction;
      if (_dateFrom != null) {
        params['date_from'] =
            DateFormat('yyyy-MM-dd').format(_dateFrom!);
      }
      if (_dateTo != null) {
        params['date_to'] = DateFormat('yyyy-MM-dd').format(_dateTo!);
      }

      final response = await _api.get('audit', queryParameters: params);
      final data = response['data'];
      final items = (data is Map ? data['items'] : data) ?? [];
      final total = data is Map ? (data['total'] ?? 0) : 0;

      setState(() {
        final newItems = (items as List).cast<Map<String, dynamic>>();
        if (reset) {
          _logs = newItems;
        } else {
          _logs.addAll(newItems);
        }
        _totalCount = total is int ? total : (total as num).toInt();
        _hasMore = newItems.length >= 50;
        _currentPage++;
        _isLoading = false;
        _isLoadingMore = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
        _isLoadingMore = false;
      });
    }
  }

  String _entityTypeLabel(String? type) {
    switch (type) {
      case 'invoice':
        return 'فاتورة';
      case 'payment':
        return 'دفعة';
      case 'purchase_order':
        return 'أمر شراء';
      case 'journal_entry':
        return 'قيد يومية';
      case 'expense':
        return 'مصروف';
      case 'workflow':
        return 'سير عمل';
      case 'user':
        return 'مستخدم';
      case 'settings':
        return 'إعدادات';
      default:
        return type ?? 'غير محدد';
    }
  }

  String _actionLabel(String? action) {
    switch (action) {
      case 'create':
        return 'إنشاء';
      case 'update':
        return 'تحديث';
      case 'delete':
        return 'حذف';
      case 'approve':
        return 'موافقة';
      case 'reject':
        return 'رفض';
      case 'post':
        return 'ترحيل';
      case 'cancel':
        return 'إلغاء';
      case 'login':
        return 'تسجيل دخول';
      case 'logout':
        return 'تسجيل خروج';
      default:
        return action ?? 'غير محدد';
    }
  }

  Color _actionColor(String? action) {
    switch (action) {
      case 'create':
        return AppColors.success;
      case 'update':
        return AppColors.edit;
      case 'delete':
        return AppColors.danger;
      case 'approve':
        return AppColors.secondary;
      case 'reject':
        return AppColors.warning;
      case 'post':
        return AppColors.primary;
      case 'cancel':
        return AppColors.buttonCancel;
      case 'login':
        return AppColors.primary;
      case 'logout':
        return AppColors.textSecondary;
      default:
        return AppColors.textSecondary;
    }
  }

  IconData _actionIcon(String? action) {
    switch (action) {
      case 'create':
        return Icons.add_circle_outline;
      case 'update':
        return Icons.edit;
      case 'delete':
        return Icons.delete_outline;
      case 'approve':
        return Icons.check_circle_outline;
      case 'reject':
        return Icons.cancel_outlined;
      case 'post':
        return Icons.send;
      case 'cancel':
        return Icons.block;
      case 'login':
        return Icons.login;
      case 'logout':
        return Icons.logout;
      default:
        return Icons.info_outline;
    }
  }

  String _formatTimestamp(String? ts) {
    if (ts == null || ts.isEmpty) return '';
    try {
      final dt = DateTime.parse(ts);
      return DateFormat('yyyy/MM/dd HH:mm:ss').format(dt);
    } catch (_) {
      return ts;
    }
  }

  // ── Detail Dialog ──────────────────────────────────────────────────
  void _showDetail(Map<String, dynamic> log) {
    final details = log['details'] ?? log['metadata'] ?? log['data'];
    String prettyJson = '';
    if (details != null) {
      try {
        prettyJson =
            const JsonEncoder.withIndent('  ').convert(details);
      } catch (_) {
        prettyJson = details.toString();
      }
    }

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تفاصيل السجل'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _detailRow(
                  'الوقت', _formatTimestamp(log['created_at'] ?? log['timestamp'])),
              _detailRow('المستخدم',
                  log['user_name'] ?? log['user'] ?? log['user_id'] ?? ''),
              _detailRow('الإجراء',
                  _actionLabel(log['action'])),
              _detailRow('نوع الكيان',
                  _entityTypeLabel(log['entity_type'])),
              _detailRow('معرف الكيان',
                  '${log['entity_id'] ?? ''}'),
              if (prettyJson.isNotEmpty) ...[
                const SizedBox(height: 8),
                const Divider(),
                const SizedBox(height: 8),
                const Text('البيانات:', style: AppTextStyles.labelLarge),
                const SizedBox(height: 4),
                Container(
                  width: double.maxFinite,
                  padding: const EdgeInsets.all(AppDimens.s1),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(AppDimens.radiusCard),
                  ),
                  child: SelectableText(
                    prettyJson,
                    style: const TextStyle(
                        fontSize: 12, fontFamily: 'monospace'),
                  ),
                ),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('إغلاق'),
          ),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            ),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );
  }

  // ── Pick Date ──────────────────────────────────────────────────────
  Future<void> _pickDate({required bool isFrom}) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: isFrom
          ? (_dateFrom ?? DateTime.now().subtract(const Duration(days: 30)))
          : (_dateTo ?? DateTime.now()),
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() {
        if (isFrom) {
          _dateFrom = picked;
        } else {
          _dateTo = picked;
        }
      });
      _loadLogs(reset: true);
    }
  }

  // ── Build ──────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('سجل التدقيق'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _loadLogs(reset: true),
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
                TextButton(onPressed: () => _loadLogs(reset: true), child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          _buildFilterBar(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: AppDimens.s2),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(bottom: BorderSide(color: AppColors.outlineVariant)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filterEntityType,
                  isDense: true,
                  decoration: const InputDecoration(
                    labelText: 'نوع الكيان',
                    border: OutlineInputBorder(),
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    isDense: true,
                  ),
                  items: [
                    const DropdownMenuItem(
                        value: null, child: Text('الكل')),
                    ..._entityTypes.map(
                      (e) => DropdownMenuItem(
                          value: e, child: Text(_entityTypeLabel(e))),
                    ),
                  ],
                  onChanged: (v) {
                    setState(() => _filterEntityType = v);
                    _loadLogs(reset: true);
                  },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filterAction,
                  isDense: true,
                  decoration: const InputDecoration(
                    labelText: 'الإجراء',
                    border: OutlineInputBorder(),
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    isDense: true,
                  ),
                  items: [
                    const DropdownMenuItem(
                        value: null, child: Text('الكل')),
                    ..._actions.map(
                      (e) => DropdownMenuItem(
                          value: e, child: Text(_actionLabel(e))),
                    ),
                  ],
                  onChanged: (v) {
                    setState(() => _filterAction = v);
                    _loadLogs(reset: true);
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _pickDate(isFrom: true),
                  icon: const Icon(Icons.calendar_today, size: 16),
                  label: Text(
                    _dateFrom != null
                        ? DateFormat('yyyy/MM/dd').format(_dateFrom!)
                        : 'من تاريخ',
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _pickDate(isFrom: false),
                  icon: const Icon(Icons.calendar_today, size: 16),
                  label: Text(
                    _dateTo != null
                        ? DateFormat('yyyy/MM/dd').format(_dateTo!)
                        : 'إلى تاريخ',
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
              ),
              if (_dateFrom != null || _dateTo != null) ...[
                const SizedBox(width: 4),
                IconButton(
                  icon: const Icon(Icons.clear, size: 18),
                  onPressed: () {
                    setState(() {
                      _dateFrom = null;
                      _dateTo = null;
                    });
                    _loadLogs(reset: true);
                  },
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_logs.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.history, size: 64, color: AppColors.textSecondary),
            SizedBox(height: 16),
            Text(
              'لا توجد سجلات',
              style: TextStyle(fontSize: 18, color: AppColors.textSecondary),
            ),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: () => _loadLogs(reset: true),
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(vertical: AppDimens.s1),
        itemCount: _logs.length + (_isLoadingMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == _logs.length) {
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          return _buildLogTile(_logs[index]);
        },
      ),
    );
  }

  Widget _buildLogTile(Map<String, dynamic> log) {
    final action = log['action'];
    final entityType = log['entity_type'];
    final entityId = log['entity_id'] ?? '';
    final userName = log['user_name'] ?? log['user'] ?? log['user_id'] ?? '';
    final timestamp = log['created_at'] ?? log['timestamp'] ?? '';

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
      ),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: AppDimens.s3, vertical: AppDimens.s1),
        leading: CircleAvatar(
          backgroundColor: _actionColor(action).withOpacity(0.1),
          child:
              Icon(_actionIcon(action), color: _actionColor(action), size: 20),
        ),
        title: Row(
          children: [
            _buildChip(_actionLabel(action), _actionColor(action)),
            const SizedBox(width: AppDimens.s2),
            _buildChip(_entityTypeLabel(entityType), AppColors.secondary),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: AppDimens.s1),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'معرف: $entityId',
                style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 2),
              Text(
                'المستخدم: $userName',
                style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 2),
              Text(
                _formatTimestamp(timestamp),
                style: TextStyle(fontSize: 11, color: AppColors.textHint),
              ),
            ],
          ),
        ),
        onTap: () => _showDetail(log),
      ),
    );
  }

  Widget _buildChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(AppDimens.radiusCard),
      ),
      child: Text(
        label,
        style: TextStyle(
            color: color, fontSize: 11, fontWeight: FontWeight.bold),
      ),
    );
  }
}
