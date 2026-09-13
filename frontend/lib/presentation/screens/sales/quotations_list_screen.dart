import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../domain/entities/quotation.dart';
import '../../../domain/entities/customer.dart';
import '../../providers/sales_provider.dart';
import '../customers/customers_list_screen.dart';

/// شاشة قائمة عروض الأسعار (Quotations List)
class QuotationsListScreen extends StatefulWidget {
  const QuotationsListScreen({Key? key}) : super(key: key);

  @override
  State<QuotationsListScreen> createState() => _QuotationsListScreenState();
}

class _QuotationsListScreenState extends State<QuotationsListScreen> {
  String _searchQuery = '';
  String _statusFilter = 'all'; // all, draft, sent, accepted, rejected

  @override
  Widget build(BuildContext context) {
    final salesProvider = Provider.of<SalesProvider>(context);
    final quotations = salesProvider.quotations;

    return Scaffold(
      appBar: AppBar(
        title: const Text('عروض الأسعار'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _navigateToQuotationForm(context, null),
            tooltip: 'إضافة عرض سعر جديد',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => salesProvider.loadQuotations(),
            tooltip: 'تحديث القائمة',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFilterBar(salesProvider),
          Expanded(
            child: quotations.isEmpty
                ? _buildEmptyState()
                : _buildQuotationsList(quotations, salesProvider),
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
                hintText: 'بحث برقم العرض أو العميل...',
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
              DropdownMenuItem(value: 'accepted', child: Text('مقبول')),
              DropdownMenuItem(value: 'rejected', child: Text('مرفوض')),
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
          Icon(Icons.description_outlined, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'لا توجد عروض أسعار',
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('إنشاء عرض سعر'),
            onPressed: () => _navigateToQuotationForm(context, null),
          ),
        ],
      ),
    );
  }

  Widget _buildQuotationsList(List<Quotation> quotations, SalesProvider salesProvider) {
    final filteredQuotations = quotations.where((q) {
      final matchesSearch = q.number.contains(_searchQuery) ||
                           q.customerName.toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesStatus = _statusFilter == 'all' || q.status == _statusFilter;
      return matchesSearch && matchesStatus;
    }).toList();

    return ListView.builder(
      itemCount: filteredQuotations.length,
      itemBuilder: (context, index) {
        final quotation = filteredQuotations[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: _getStatusIcon(quotation.status),
            title: Text(quotation.number),
            subtitle: Text('${quotation.customerName}\n${_formatDate(quotation.date)}'),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${quotation.totalAmount.toStringAsFixed(2)} ${quotation.currency}',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                Text(
                  _getStatusText(quotation.status),
                  style: TextStyle(
                    fontSize: 12,
                    color: _getStatusColor(quotation.status),
                  ),
                ),
              ],
            ),
            onTap: () => _navigateToQuotationForm(context, quotation),
            onLongPress: () => _showActionsMenu(context, quotation, salesProvider),
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
      case 'accepted':
        icon = Icons.check_circle;
        color = Colors.green;
        break;
      case 'rejected':
        icon = Icons.cancel;
        color = Colors.red;
        break;
      default:
        icon = Icons.description;
        color = Colors.grey;
    }
    
    return Icon(icon, color: color, size: 32);
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'draft': return 'مسودة';
      case 'sent': return 'مُرسل';
      case 'accepted': return 'مقبول';
      case 'rejected': return 'مرفوض';
      default: return status;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'draft': return Colors.grey;
      case 'sent': return Colors.blue;
      case 'accepted': return Colors.green;
      case 'rejected': return Colors.red;
      default: return Colors.grey;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }

  void _navigateToQuotationForm(BuildContext context, Quotation? quotation) {
    // TODO: Navigate to QuotationFormScreen
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(quotation == null ? 'إنشاء عرض سعر جديد' : 'تعديل عرض السعر ${quotation.number}')),
    );
  }

  void _showActionsMenu(BuildContext context, Quotation quotation, SalesProvider salesProvider) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (quotation.status == 'draft') ...[
              ListTile(
                leading: const Icon(Icons.send),
                title: const Text('إرسال العرض'),
                onTap: () {
                  salesProvider.sendQuotation(quotation.id);
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.edit),
                title: const Text('تعديل'),
                onTap: () {
                  _navigateToQuotationForm(context, quotation);
                  Navigator.pop(context);
                },
              ),
            ],
            if (quotation.status == 'sent') ...[
              ListTile(
                leading: const Icon(Icons.check_circle, color: Colors.green),
                title: const Text('قبول وتحويل لطلب بيع'),
                onTap: () {
                  salesProvider.acceptQuotation(quotation.id);
                  Navigator.pop(context);
                  // TODO: Navigate to Sales Order creation with quotation data
                },
              ),
              ListTile(
                leading: const Icon(Icons.cancel, color: Colors.red),
                title: const Text('رفض العرض'),
                onTap: () {
                  salesProvider.rejectQuotation(quotation.id);
                  Navigator.pop(context);
                },
              ),
            ],
            ListTile(
              leading: const Icon(Icons.delete, color: Colors.red),
              title: const Text('حذف'),
              onTap: () {
                _confirmDelete(context, quotation, salesProvider);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmDelete(BuildContext context, Quotation quotation, SalesProvider salesProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('تأكيد الحذف'),
        content: Text('هل أنت متأكد من حذف عرض السعر ${quotation.number}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              salesProvider.deleteQuotation(quotation.id);
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
