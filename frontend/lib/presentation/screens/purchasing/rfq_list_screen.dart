import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../domain/entities/rfq.dart';
import '../../providers/purchasing_provider.dart';
import '../suppliers/suppliers_list_screen.dart';

/// شاشة قائمة طلبات عروض الأسعار (RFQ List)
class RFQListScreen extends StatefulWidget {
  const RFQListScreen({Key? key}) : super(key: key);

  @override
  State<RFQListScreen> createState() => _RFQListScreenState();
}

class _RFQListScreenState extends State<RFQListScreen> {
  String _searchQuery = '';
  String _statusFilter = 'all'; // all, draft, sent, received, evaluated, converted, cancelled

  @override
  Widget build(BuildContext context) {
    final purchasingProvider = Provider.of<PurchasingProvider>(context);
    final rfqs = purchasingProvider.rfqs;

    return Scaffold(
      appBar: AppBar(
        title: const Text('طلبات عروض الأسعار'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _navigateToRFQForm(context, null),
            tooltip: 'إضافة طلب عرض سعر جديد',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => purchasingProvider.loadRFQs(),
            tooltip: 'تحديث القائمة',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterBar(purchasingProvider),
          Expanded(
            child: rfqs.isEmpty
                ? _buildEmptyState()
                : _buildRFQsList(rfqs, purchasingProvider),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar(PurchasingProvider purchasingProvider) {
    return Container(
      padding: const EdgeInsets.all(16),
      color: Colors.grey[100],
      child: Row(
        children: [
          Expanded(
            child: TextField(
              decoration: InputDecoration(
                hintText: 'بحث برقم الطلب أو المورد...',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              onChanged: (value) => setState(() => _searchQuery = value),
            ),
          ),
          const SizedBox(width: 16),
          DropdownButton<String>(
            value: _statusFilter,
            items: const [
              DropdownMenuItem(value: 'all', child: Text('الكل')),
              DropdownMenuItem(value: 'draft', child: Text('مسودة')),
              DropdownMenuItem(value: 'sent', child: Text('مُرسل')),
              DropdownMenuItem(value: 'received', child: Text('مستلم')),
              DropdownMenuItem(value: 'evaluated', child: Text('تم التقييم')),
              DropdownMenuItem(value: 'converted', child: Text('مُحوّل لطلبية')),
              DropdownMenuItem(value: 'cancelled', child: Text('ملغي')),
            ],
            onChanged: (value) => setState(() => _statusFilter = value!),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.request_quote_outlined, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'لا توجد طلبات عروض أسعار',
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('إنشاء طلب عرض سعر'),
            onPressed: () => _navigateToRFQForm(context, null),
          ),
        ],
      ),
    );
  }

  Widget _buildRFQsList(List<RFQ> rfqs, PurchasingProvider purchasingProvider) {
    final filteredRFQs = rfqs.where((r) {
      final matchesSearch = r.number.contains(_searchQuery) ||
                           r.supplierName.toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesStatus = _statusFilter == 'all' || r.status == _statusFilter;
      return matchesSearch && matchesStatus;
    }).toList();

    return ListView.builder(
      itemCount: filteredRFQs.length,
      itemBuilder: (context, index) {
        final rfq = filteredRFQs[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: _getStatusIcon(rfq.status),
            title: Text(rfq.number),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(rfq.supplierName),
                Text('${_formatDate(rfq.date)} • ${rfq.itemsCount} أصناف'),
                if (rfq.deadline != null)
                  Text('آخر موعد: ${_formatDate(rfq.deadline!)}',
                      style: TextStyle(fontSize: 12, color: Colors.red[700])),
              ],
            ),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  _getStatusText(rfq.status),
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: _getStatusColor(rfq.status),
                  ),
                ),
                if (rfq.quotationReceived)
                  const Text(
                    'عرض السعر وارد',
                    style: TextStyle(fontSize: 10, color: Colors.green),
                  ),
              ],
            ),
            onTap: () => _navigateToRFQForm(context, rfq),
            onLongPress: () => _showActionsMenu(context, rfq, purchasingProvider),
          ),
        );
      },
    );
  }

  Widget _getStatusIcon(String status) {
    IconData icon;
    Color color;
    
    switch (status) {
      case 'draft':
        icon = Icons.file_present;
        color = Colors.grey;
        break;
      case 'sent':
        icon = Icons.send;
        color = Colors.blue;
        break;
      case 'received':
        icon = Icons.mark_email_read;
        color = Colors.orange;
        break;
      case 'evaluated':
        icon = Icons.rate_review;
        color = Colors.purple;
        break;
      case 'converted':
        icon = Icons.shopping_cart;
        color = Colors.green;
        break;
      case 'cancelled':
        icon = Icons.cancel;
        color = Colors.red;
        break;
      default:
        icon = Icons.request_quote;
        color = Colors.grey;
    }
    
    return Icon(icon, color: color, size: 32);
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'draft': return 'مسودة';
      case 'sent': return 'مُرسل';
      case 'received': return 'مستلم';
      case 'evaluated': return 'تم التقييم';
      case 'converted': return 'مُحوّل';
      case 'cancelled': return 'ملغي';
      default: return status;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'draft': return Colors.grey;
      case 'sent': return Colors.blue;
      case 'received': return Colors.orange;
      case 'evaluated': return Colors.purple;
      case 'converted': return Colors.green;
      case 'cancelled': return Colors.red;
      default: return Colors.grey;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }

  void _navigateToRFQForm(BuildContext context, RFQ? rfq) {
    // TODO: Navigate to RFQFormScreen
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(rfq == null ? 'إنشاء طلب عرض سعر جديد' : 'تعديل طلب عرض السعر ${rfq.number}')),
    );
  }

  void _showActionsMenu(BuildContext context, RFQ rfq, PurchasingProvider purchasingProvider) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (rfq.status == 'draft') ...[
              ListTile(
                leading: const Icon(Icons.send),
                title: const Text('إرسال للمورد'),
                onTap: () {
                  purchasingProvider.sendRFQ(rfq.id);
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.edit),
                title: const Text('تعديل'),
                onTap: () {
                  _navigateToRFQForm(context, rfq);
                  Navigator.pop(context);
                },
              ),
            ],
            if (rfq.status == 'sent' && rfq.quotationReceived) ...[
              ListTile(
                leading: const Icon(Icons.rate_review),
                title: const Text('تقييم العرض'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to RFQ evaluation screen
                },
              ),
            ],
            if (rfq.status == 'evaluated') ...[
              ListTile(
                leading: const Icon(Icons.shopping_cart, color: Colors.green),
                title: const Text('تحويل لطلبية شراء'),
                onTap: () {
                  purchasingProvider.convertRFQToPO(rfq.id);
                  Navigator.pop(context);
                  // TODO: Navigate to PO creation with RFQ data
                },
              ),
            ],
            if (rfq.status != 'cancelled' && rfq.status != 'converted') ...[
              ListTile(
                leading: const Icon(Icons.cancel, color: Colors.red),
                title: const Text('إلغاء الطلب'),
                onTap: () {
                  _confirmCancel(context, rfq, purchasingProvider);
                  Navigator.pop(context);
                },
              ),
            ],
            ListTile(
              leading: const Icon(Icons.delete, color: Colors.red),
              title: const Text('حذف'),
              onTap: () {
                _confirmDelete(context, rfq, purchasingProvider);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmCancel(BuildContext context, RFQ rfq, PurchasingProvider purchasingProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الإلغاء'),
        content: Text('هل أنت متأكد من إلغاء طلب عرض السعر ${rfq.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              purchasingProvider.cancelRFQ(rfq.id);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('إلغاء'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(BuildContext context, RFQ rfq, PurchasingProvider purchasingProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف طلب عرض السعر ${rfq.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              purchasingProvider.deleteRFQ(rfq.id);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('حذف'),
          ),
        ],
      ),
    );
  }
}
