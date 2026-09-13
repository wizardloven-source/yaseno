import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../domain/entities/delivery.dart';
import '../../providers/inventory_provider.dart';
import '../sales/sales_orders_list_screen.dart';

/// شاشة قائمة التوصيلات/التسليم (Delivery/Picking List)
class DeliveryListScreen extends StatefulWidget {
  const DeliveryListScreen({Key? key}) : super(key: key);

  @override
  State<DeliveryListScreen> createState() => _DeliveryListScreenState();
}

class _DeliveryListScreenState extends State<DeliveryListScreen> {
  String _searchQuery = '';
  String _statusFilter = 'all'; // all, draft, picking, ready, delivered, cancelled

  @override
  Widget build(BuildContext context) {
    final inventoryProvider = Provider.of<InventoryProvider>(context);
    final deliveries = inventoryProvider.deliveries;

    return Scaffold(
      appBar: AppBar(
        title: const Text('التوصيلات والتسليم'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _navigateToDeliveryForm(context, null),
            tooltip: 'إضافة توصيلة جديدة',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => inventoryProvider.loadDeliveries(),
            tooltip: 'تحديث القائمة',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterBar(inventoryProvider),
          Expanded(
            child: deliveries.isEmpty
                ? _buildEmptyState()
                : _buildDeliveriesList(deliveries, inventoryProvider),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar(InventoryProvider inventoryProvider) {
    return Container(
      padding: const EdgeInsets.all(16),
      color: Colors.grey[100],
      child: Row(
        children: [
          Expanded(
            child: TextField(
              decoration: InputDecoration(
                hintText: 'بحث برقم التوصيلة أو العميل...',
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
              DropdownMenuItem(value: 'picking', child: Text('جاري الانتقاء')),
              DropdownMenuItem(value: 'ready', child: Text('جاهزة للتسليم')),
              DropdownMenuItem(value: 'delivered', child: Text('مُسلّمة')),
              DropdownMenuItem(value: 'cancelled', child: Text('ملغاة')),
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
          Icon(Icons.local_shipping_outlined, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'لا توجد توصيلات',
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('إنشاء توصيلة'),
            onPressed: () => _navigateToDeliveryForm(context, null),
          ),
        ],
      ),
    );
  }

  Widget _buildDeliveriesList(List<Delivery> deliveries, InventoryProvider inventoryProvider) {
    final filteredDeliveries = deliveries.where((d) {
      final matchesSearch = d.number.contains(_searchQuery) ||
                           d.customerName.toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesStatus = _statusFilter == 'all' || d.status == _statusFilter;
      return matchesSearch && matchesStatus;
    }).toList();

    return ListView.builder(
      itemCount: filteredDeliveries.length,
      itemBuilder: (context, index) {
        final delivery = filteredDeliveries[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: _getStatusIcon(delivery.status),
            title: Text(delivery.number),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(delivery.customerName),
                Text('${_formatDate(delivery.date)} • ${delivery.itemsCount} أصناف'),
                if (delivery.salesOrderNumber != null)
                  Text('أمر بيع: ${delivery.salesOrderNumber}',
                      style: const TextStyle(fontSize: 12, color: Colors.blue)),
                if (delivery.warehouseName != null)
                  Text('المستودع: ${delivery.warehouseName}',
                      style: const TextStyle(fontSize: 12)),
              ],
            ),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  _getStatusText(delivery.status),
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: _getStatusColor(delivery.status),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${delivery.pickedQuantity}/${delivery.totalQuantity}',
                  style: const TextStyle(fontSize: 12),
                ),
                const Text('منتقى', style: TextStyle(fontSize: 10)),
              ],
            ),
            onTap: () => _navigateToDeliveryForm(context, delivery),
            onLongPress: () => _showActionsMenu(context, delivery, inventoryProvider),
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
      case 'picking':
        icon = Icons.inventory_2;
        color = Colors.orange;
        break;
      case 'ready':
        icon = Icons.check_circle_outline;
        color = Colors.blue;
        break;
      case 'delivered':
        icon = Icons.delivery_dining;
        color = Colors.green;
        break;
      case 'cancelled':
        icon = Icons.cancel;
        color = Colors.red;
        break;
      default:
        icon = Icons.local_shipping;
        color = Colors.grey;
    }
    
    return Icon(icon, color: color, size: 32);
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'draft': return 'مسودة';
      case 'picking': return 'جاري الانتقاء';
      case 'ready': return 'جاهزة';
      case 'delivered': return 'مُسلّمة';
      case 'cancelled': return 'ملغاة';
      default: return status;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'draft': return Colors.grey;
      case 'picking': return Colors.orange;
      case 'ready': return Colors.blue;
      case 'delivered': return Colors.green;
      case 'cancelled': return Colors.red;
      default: return Colors.grey;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }

  void _navigateToDeliveryForm(BuildContext context, Delivery? delivery) {
    // TODO: Navigate to DeliveryFormScreen
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(delivery == null ? 'إنشاء توصيلة جديدة' : 'تعديل التوصيلة ${delivery.number}')),
    );
  }

  void _showActionsMenu(BuildContext context, Delivery delivery, InventoryProvider inventoryProvider) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (delivery.status == 'draft') ...[
              ListTile(
                leading: const Icon(Icons.inventory_2),
                title: const Text('بدء الانتقاء'),
                onTap: () {
                  inventoryProvider.startPicking(delivery.id);
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.edit),
                title: const Text('تعديل'),
                onTap: () {
                  _navigateToDeliveryForm(context, delivery);
                  Navigator.pop(context);
                },
              ),
            ],
            if (delivery.status == 'picking') ...[
              ListTile(
                leading: const Icon(Icons.check_circle, color: Colors.green),
                title: const Text('اكتمل الانتقاء'),
                onTap: () {
                  inventoryProvider.completePicking(delivery.id);
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.qr_code_scanner),
                title: const Text('مسح الباركود'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Open barcode scanner for picking
                },
              ),
            ],
            if (delivery.status == 'ready') ...[
              ListTile(
                leading: const Icon(Icons.local_shipping, color: Colors.green),
                title: const Text('تأكيد التسليم'),
                onTap: () {
                  inventoryProvider.confirmDelivery(delivery.id);
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.print),
                title: const Text('طباعة ورقة التسليم'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Print delivery note
                },
              ),
            ],
            if (delivery.status == 'delivered') ...[
              ListTile(
                leading: const Icon(Icons.receipt, color: Colors.blue),
                title: const Text('إنشاء فاتورة'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to Invoice creation with delivery data
                },
              ),
            ],
            if (delivery.status != 'cancelled' && delivery.status != 'delivered') ...[
              ListTile(
                leading: const Icon(Icons.cancel, color: Colors.red),
                title: const Text('إلغاء التوصيلة'),
                onTap: () {
                  _confirmCancel(context, delivery, inventoryProvider);
                  Navigator.pop(context);
                },
              ),
            ],
            ListTile(
              leading: const Icon(Icons.delete, color: Colors.red),
              title: const Text('حذف'),
              onTap: () {
                _confirmDelete(context, delivery, inventoryProvider);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmCancel(BuildContext context, Delivery delivery, InventoryProvider inventoryProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الإلغاء'),
        content: Text('هل أنت متأكد من إلغاء التوصيلة ${delivery.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              inventoryProvider.cancelDelivery(delivery.id);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('إلغاء'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(BuildContext context, Delivery delivery, InventoryProvider inventoryProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف التوصيلة ${delivery.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              inventoryProvider.deleteDelivery(delivery.id);
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
