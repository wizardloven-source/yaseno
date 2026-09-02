import 'package:flutter/material.dart';
import 'package:ya_seen_erp_flutter/services/api_service.dart';
import 'package:intl/intl.dart';
import '../../../utils/error_utils.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_dimensions.dart';
import '../../../theme/app_text_styles.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _notifications = [];
  int _unreadCount = 0;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _api.get('notifications'),
        _api.get('notifications/unread-count'),
      ]);
      final listResp = results[0];
      final countResp = results[1];

      final listData = listResp['data'];
      final listItems = (listData is Map ? listData['items'] : listData) ?? [];

      final countData = countResp['data'] ?? countResp;
      final unread = countData is Map
          ? (countData['count'] ?? countData['unread_count'] ?? 0)
          : 0;

      setState(() {
        _notifications =
            (listItems as List).cast<Map<String, dynamic>>();
        _unreadCount = unread is int ? unread : (unread as num).toInt();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = ErrorUtils.sanitize(e);
        _isLoading = false;
      });
    }
  }

  Future<void> _markAsRead(String id) async {
    try {
      await _api.post('notifications/$id/read');
      setState(() {
        final idx = _notifications.indexWhere(
            (n) => (n['id'] ?? '').toString() == id);
        if (idx != -1) {
          _notifications[idx]['is_read'] = true;
          _notifications[idx]['read'] = true;
        }
        if (_unreadCount > 0) _unreadCount--;
      });
    } catch (_) {}
  }

  Future<void> _markAllAsRead() async {
    try {
      await _api.post('notifications/read-all');
      setState(() {
        for (var n in _notifications) {
          n['is_read'] = true;
          n['read'] = true;
        }
        _unreadCount = 0;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم تحديد الكل كمقروء'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ErrorUtils.sanitize(e)), backgroundColor: AppColors.danger),
        );
      }
    }
  }

  bool _isRead(Map<String, dynamic> n) {
    return n['is_read'] == true || n['read'] == true;
  }

  String _formatTimestamp(String? ts) {
    if (ts == null || ts.isEmpty) return '';
    try {
      final dt = DateTime.parse(ts);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inMinutes < 1) return 'الآن';
      if (diff.inMinutes < 60) return 'منذ ${diff.inMinutes} دقيقة';
      if (diff.inHours < 24) return 'منذ ${diff.inHours} ساعة';
      if (diff.inDays < 7) return 'منذ ${diff.inDays} يوم';
      return DateFormat('yyyy/MM/dd HH:mm').format(dt);
    } catch (_) {
      return ts;
    }
  }

  IconData _notifIcon(String? type) {
    switch (type) {
      case 'approval':
        return Icons.approval;
      case 'workflow':
        return Icons.account_tree;
      case 'payment':
        return Icons.payment;
      case 'invoice':
        return Icons.receipt_long;
      case 'error':
        return Icons.error_outline;
      default:
        return Icons.notifications;
    }
  }

  Color _notifColor(String? type) {
    switch (type) {
      case 'approval':
        return AppColors.warning;
      case 'workflow':
        return AppColors.secondary;
      case 'payment':
        return AppColors.success;
      case 'invoice':
        return AppColors.secondary;
      case 'error':
        return AppColors.danger;
      default:
        return AppColors.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الإشعارات'),
        centerTitle: true,
        actions: [
          if (_unreadCount > 0)
            TextButton.icon(
              onPressed: _markAllAsRead,
              icon: const Icon(Icons.done_all, color: AppColors.primary),
              label: const Text(
                'تحديد الكل كمقروء',
                style: TextStyle(color: AppColors.primary),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadAll,
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
                TextButton(onPressed: _loadAll, child: const Text('إعادة المحاولة')),
              ],
              backgroundColor: AppColors.warningContainer,
            ),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_notifications.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.notifications_none, size: 64, color: AppColors.textSecondary),
            const SizedBox(height: 16),
            Text(
              'لا توجد إشعارات',
              style: AppTextStyles.headlineSmall.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _loadAll,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(vertical: AppDimens.s1),
        itemCount: _notifications.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, index) =>
            _buildNotificationTile(_notifications[index]),
      ),
    );
  }

  Widget _buildNotificationTile(Map<String, dynamic> n) {
    final id = (n['id'] ?? '').toString();
    final title = n['title'] ?? '';
    final message = n['message'] ?? '';
    final timestamp = n['created_at'] ?? n['timestamp'] ?? '';
    final read = _isRead(n);
    final type = n['type'];

    return ListTile(
      tileColor: read ? null : AppColors.secondary.withValues(alpha: 0.04),
      leading: Stack(
        children: [
          CircleAvatar(
            backgroundColor: _notifColor(type).withOpacity(0.1),
            child: Icon(_notifIcon(type), color: _notifColor(type), size: 20),
          ),
          if (!read)
            Positioned(
              top: 0,
              right: 0,
              child: Container(
                width: 10,
                height: 10,
                decoration: const BoxDecoration(
                  color: AppColors.secondary,
                  shape: BoxShape.circle,
                ),
              ),
            ),
        ],
      ),
      title: Text(
        title,
        style: TextStyle(
          fontWeight: read ? FontWeight.normal : FontWeight.bold,
          fontSize: 14,
        ),
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 2),
          Text(
            message,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 12,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            _formatTimestamp(timestamp),
            style: TextStyle(fontSize: 11, color: AppColors.textMuted),
          ),
        ],
      ),
      onTap: () {
        if (!read) _markAsRead(id);
      },
    );
  }
}
