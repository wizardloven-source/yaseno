import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../domain/entities/goods_receipt.dart';
import '../../providers/inventory_provider.dart';
import '../purchasing/purchase_order_list_screen.dart';

/// شاشة قائمة استلام البضائع (Goods Receipt List)
class GoodsReceiptListScreen extends StatefulWidget {
  const GoodsReceiptListScreen({Key? key}) : super(key: key);

  @override
  State<GoodsReceiptListScreen> createState() => _GoodsReceiptListScreenState();
}

class _GoodsReceiptListScreenState extends State<GoodsReceiptListScreen> {
  String _searchQuery = '';
  String _statusFilter = 'all'; // all, draft, partial, completed, cancelled

  @override
  Widget build(BuildContext context) {
    final inventoryProvider = Provider.of<InventoryProvider>(context);
    final receipts = inventoryProvider.goodsReceipts;

    return Scaffold(
      appBar: AppBar(
        title: const Text('استلام البضائع'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _navigateToReceiptForm(context, null),
            tooltip: 'إضافة استلام بضاعة جديد',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => inventoryProvider.loadGoodsReceipts(),
            tooltip: 'تحديث القائمة',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterBar(inventoryProvider),
          Expanded(
            child: receipts.isEmpty
                ? _buildEmptyState()
                : _buildReceiptsList(receipts, inventoryProvider),
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
                hintText: 'بحث برقم الاستلام أو المورد...',
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
              DropdownMenuItem(value: 'partial', child: Text('استلام جزئي')),
              DropdownMenuItem(value: 'completed', child: Text('مكتمل')),
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
          Icon(Icons.inventory_2_outlined, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'لا توجد عمليات استلام',
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('إنشاء استلام بضاعة'),
            onPressed: () => _navigateToReceiptForm(context, null),
          ),
        ],
      ),
    );
  }

  Widget _buildReceiptsList(List<GoodsReceipt> receipts, InventoryProvider inventoryProvider) {
    final filteredReceipts = receipts.where((r) {
      final matchesSearch = r.number.contains(_searchQuery) ||
                           r.supplierName.toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesStatus = _statusFilter == 'all' || r.status == _statusFilter;
      return matchesSearch && matchesStatus;
    }).toList();

    return ListView.builder(
      itemCount: filteredReceipts.length,
      itemBuilder: (context, index) {
        final receipt = filteredReceipts[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: _getStatusIcon(receipt.status),
            title: Text(receipt.number),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(receipt.supplierName),
                Text('${_formatDate(receipt.date)} • ${receipt.itemsCount} أصناف'),
                if (receipt.purchaseOrderNumber != null)
                  Text('طلبية شراء: ${receipt.purchaseOrderNumber}',
                      style: const TextStyle(fontSize: 12, color: Colors.blue)),
                if (receipt.warehouseName != null)
                  Text('المستودع: ${receipt.warehouseName}',
                      style: const TextStyle(fontSize: 12)),
              ],
            ),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  _getStatusText(receipt.status),
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: _getStatusColor(receipt.status),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${receipt.receivedQuantity}/${receipt.expectedQuantity}',
                  style: const TextStyle(fontSize: 12),
                ),
                const Text('مستلم', style: TextStyle(fontSize: 10)),
                if (receipt.isPartiallyReceived)
                  const Text(
                    'جزئي',
                    style: TextStyle(fontSize: 10, color: Colors.orange),
                  ),
              ],
            ),
            onTap: () => _navigateToReceiptForm(context, receipt),
            onLongPress: () => _showActionsMenu(context, receipt, inventoryProvider),
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
      case 'partial':
        icon = Icons.inventory_2;
        color = Colors.orange;
        break;
      case 'completed':
        icon = Icons.check_circle;
        color = Colors.green;
        break;
      case 'cancelled':
        icon = Icons.cancel;
        color = Colors.red;
        break;
      default:
        icon = Icons.inventory;
        color = Colors.grey;
    }
    
    return Icon(icon, color: color, size: 32);
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'draft': return 'مسودة';
      case 'partial': return 'استلام جزئي';
      case 'completed': return 'مكتمل';
      case 'cancelled': return 'ملغي';
      default: return status;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'draft': return Colors.grey;
      case 'partial': return Colors.orange;
      case 'completed': return Colors.green;
      case 'cancelled': return Colors.red;
      default: return Colors.grey;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }

  void _navigateToReceiptForm(BuildContext context, GoodsReceipt? receipt) {
    // TODO: Navigate to GoodsReceiptFormScreen
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(receipt == null ? 'إنشاء استلام بضاعة جديد' : 'تعديل استلام البضاعة ${receipt.number}')),
    );
  }

  void _showActionsMenu(BuildContext context, GoodsReceipt receipt, InventoryProvider inventoryProvider) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (receipt.status == 'draft') ...[
              ListTile(
                leading: const Icon(Icons.qr_code_scanner),
                title: const Text('مسح الباركود'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Open barcode scanner for receiving
                },
              ),
              ListTile(
                leading: const Icon(Icons.edit),
                title: const Text('تعديل'),
                onTap: () {
                  _navigateToReceiptForm(context, receipt);
                  Navigator.pop(context);
                },
              ),
            ],
            if (receipt.status == 'draft' || receipt.status == 'partial') ...[
              ListTile(
                leading: const Icon(Icons.add_shopping_cart, color: Colors.green),
                title: const Text('تسجيل استلام إضافي'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Add received quantities
                },
              ),
            ],
            if (receipt.status == 'partial' || receipt.status == 'draft') ...[
              ListTile(
                leading: const Icon(Icons.check_circle, color: Colors.green),
                title: const Text('تأكيد اكتمال الاستلام'),
                onTap: () {
                  inventoryProvider.completeReceipt(receipt.id);
                  Navigator.pop(context);
                },
              ),
            ],
            if (receipt.status == 'completed') ...[
              ListTile(
                leading: const Icon(Icons.receipt_long, color: Colors.blue),
                title: const Text('إنشاء فاتورة مورد'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Navigate to Supplier Bill creation with receipt data
                },
              ),
              ListTile(
                leading: const Icon(Icons.print),
                title: const Text('طباعة شهادة الاستلام'),
                onTap: () {
                  Navigator.pop(context);
                  // TODO: Print goods receipt note
                },
              ),
            ],
            if (receipt.status != 'cancelled' && receipt.status != 'completed') ...[
              ListTile(
                leading: const Icon(Icons.cancel, color: Colors.red),
                title: const Text('إلغاء الاستلام'),
                onTap: () {
                  _confirmCancel(context, receipt, inventoryProvider);
                  Navigator.pop(context);
                },
              ),
            ],
            ListTile(
              leading: const Icon(Icons.delete, color: Colors.red),
              title: const Text('حذف'),
              onTap: () {
                _confirmDelete(context, receipt, inventoryProvider);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmCancel(BuildContext context, GoodsReceipt receipt, InventoryProvider inventoryProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الإلغاء'),
        content: Text('هل أنت متأكد من إلغاء استلام البضاعة ${receipt.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              inventoryProvider.cancelReceipt(receipt.id);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('إلغاء'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(BuildContext context, GoodsReceipt receipt, InventoryProvider inventoryProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف استلام البضاعة ${receipt.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              inventoryProvider.deleteReceipt(receipt.id);
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
