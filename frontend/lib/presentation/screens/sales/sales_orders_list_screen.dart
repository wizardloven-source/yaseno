import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../domain/entities/sales_order.dart';
import '../../providers/sales_provider.dart';
import '../customers/customers_list_screen.dart';

/// شاشة قائمة أوامر البيع (Sales Orders List)
class SalesOrdersListScreen extends StatefulWidget {
  const SalesOrdersListScreen({Key? key}) : super(key: key);

  @override
  State<SalesOrdersListScreen> createState() => _SalesOrdersListScreenState();
}

class _SalesOrdersListScreenState extends State<SalesOrdersListScreen> {
  String _searchQuery = '';
  String _statusFilter = 'all'; // all, draft, confirmed, processing, delivered, invoiced, cancelled

  @override
  Widget build(BuildContext context) {
    final salesProvider = Provider.of<SalesProvider>(context);
    final orders = salesProvider.salesOrders;

    return Scaffold(
      appBar: AppBar(
        title: const Text('أوامر البيع'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _navigateToOrderForm(context, null),
            tooltip: 'إضافة أمر بيع جديد',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => salesProvider.loadSalesOrders(),
            tooltip: 'تحديث القائمة',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterBar(salesProvider),
          Expanded(
            child: orders.isEmpty
                ? _buildEmptyState()
                : _buildOrdersList(orders, salesProvider),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar(SalesProvider salesProvider) {
    return Container(
      padding: const EdgeInsets.all(16),
      color: Colors.grey[100],
      child: Row(
        children: [
          Expanded(
            child: TextField(
              decoration: InputDecoration(
                hintText: 'بحث برقم الأمر أو العميل...',
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
              DropdownMenuItem(value: 'confirmed', child: Text('مؤكد')),
              DropdownMenuItem(value: 'processing', child: Text('قيد المعالجة')),
              DropdownMenuItem(value: 'delivered', child: Text('مُسلّم')),
              DropdownMenuItem(value: 'invoiced', child: Text('مُفوتَر')),
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
          Icon(Icons.shopping_cart_outlined, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'لا توجد أوامر بيع',
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('إنشاء أمر بيع'),
            onPressed: () => _navigateToOrderForm(context, null),
          ),
        ],
      ),
    );
  }

  Widget _buildOrdersList(List<SalesOrder> orders, SalesProvider salesProvider) {
    final filteredOrders = orders.where((o) {
      final matchesSearch = o.number.contains(_searchQuery) ||
                           o.customerName.toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesStatus = _statusFilter == 'all' || o.status == _statusFilter;
      return matchesSearch && matchesStatus;
    }).toList();

    return ListView.builder(
      itemCount: filteredOrders.length,
      itemBuilder: (context, index) {
        final order = filteredOrders[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: _getStatusIcon(order.status),
            title: Text(order.number),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(order.customerName),
                Text('${_formatDate(order.date)} • ${order.itemsCount} أصناف'),
                if (order.deliveryDate != null)
                  Text('تاريخ التوصيل: ${_formatDate(order.deliveryDate!)}',
                      style: TextStyle(fontSize: 12, color: Colors.blue[700])),
              ],
            ),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${order.totalAmount.toStringAsFixed(2)} ${order.currency}',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                Text(
                  _getStatusText(order.status),
                  style: TextStyle(
                    fontSize: 12,
                    color: _getStatusColor(order.status),
                  ),
                ),
                if (order.isPartiallyDelivered)
                  const Text(
                    'توصيل جزئي',
                    style: TextStyle(fontSize: 10, color: Colors.orange),
                  ),
              ],
            ),
            onTap: () => _navigateToOrderForm(context, order),
            onLongPress: () => _showActionsMenu(context, order, salesProvider),
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
      case 'confirmed':
        icon = Icons.check_circle_outline;
        color = Colors.blue;
        break;
      case 'processing':
        icon = Icons.hourglass_empty;
        color = Colors.orange;
        break;
      case 'delivered':
        icon = Icons.local_shipping;
        color = Colors.green;
        break;
      case 'invoiced':
        icon = Icons.receipt_long;
        color = Colors.teal;
        break;
      case 'cancelled':
        icon = Icons.cancel;
        color = Colors.red;
        break;
      default:
        icon = Icons.shopping_cart;
        color = Colors.grey;
    }
    
    return Icon(icon, color: color, size: 32);
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'draft': return 'مسودة';
      case 'confirmed': return 'مؤكد';
      case 'processing': return 'قيد المعالجة';
      case 'delivered': return 'مُسلّم';
      case 'invoiced': return 'مُفوتَر';
      case 'cancelled': return 'ملغي';
      default: return status;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'draft': return Colors.grey;
      case 'confirmed': return Colors.blue;
      case 'processing': return Colors.orange;
      case 'delivered': return Colors.green;
      case 'invoiced': return Colors.teal;
      case 'cancelled': return Colors.red;
      default: return Colors.grey;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }

  void _navigateToOrderForm(BuildContext context, SalesOrder? order) {
    // TODO: Navigate to SalesOrderFormScreen
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(order == null ? 'إنشاء أمر بيع جديد' : 'تعديل أمر البيع ${order.number}')),
    );
  }

  void _showActionsMenu(BuildContext context, SalesOrder order, SalesProvider salesProvider) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (order.status == 'draft') ...[
              ListTile(
                leading: const Icon(Icons.check_circle, color: Colors.green),
                title: const Text('تأكيد الطلب'),
                onTap: () {
                  salesProvider.confirmOrder(order.id);
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.edit),
                title: const Text('تعديل'),
                onTap: () {
                  _navigateToOrderForm(context, order);
                  Navigator.pop(context);
                },
              ),
            ],
            if (order.status == 'confirmed') ...[
              ListTile(
                leading: const Icon(Icons.local_shipping),
                title: const Text('إنشاء توصيلة'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to Delivery creation with order data
                },
              ),
            ],
            if (order.status == 'delivered' && !order.isInvoiced) ...[
              ListTile(
                leading: const Icon(Icons.receipt, color: Colors.blue),
                title: const Text('إنشاء فاتورة'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to Invoice creation with order data
                },
              ),
            ],
            if (order.status != 'cancelled' && order.status != 'invoiced') ...[
              ListTile(
                leading: const Icon(Icons.cancel, color: Colors.red),
                title: const Text('إلغاء الطلب'),
                onTap: () {
                  _confirmCancel(context, order, salesProvider);
                  Navigator.pop(context);
                },
              ),
            ],
            ListTile(
              leading: const Icon(Icons.delete, color: Colors.red),
              title: const Text('حذف'),
              onTap: () {
                _confirmDelete(context, order, salesProvider);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmCancel(BuildContext context, SalesOrder order, SalesProvider salesProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الإلغاء'),
        content: Text('هل أنت متأكد من إلغاء أمر البيع ${order.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              salesProvider.cancelOrder(order.id);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('إلغاء'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(BuildContext context, SalesOrder order, SalesProvider salesProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف أمر البيع ${order.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              salesProvider.deleteOrder(order.id);
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
