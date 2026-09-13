import 'package:flutter/material.dart';
import '../../../domain/entities/permission.dart';
import '../../providers/auth_provider.dart';

/// mixin لربط الصلاحيات بالأزرار في الواجهات
/// يستخدم لإظهار/إخفاء الأزرار بناءً على صلاحيات المستخدم
mixin PermissionMixin<T extends StatefulWidget> on State<T> {
  AuthProvider get authProvider => AuthProvider.of(context);
  
  /// التحقق من وجود صلاحية معينة
  bool hasPermission(String permissionCode) {
    return authProvider.hasPermission(permissionCode);
  }
  
  /// التحقق من وجود أي صلاحية من قائمة صلاحيات
  bool hasAnyPermission(List<String> permissionCodes) {
    return permissionCodes.any((code) => hasPermission(code));
  }
  
  /// التحقق من وجود جميع الصلاحيات في القائمة
  bool hasAllPermissions(List<String> permissionCodes) {
    return permissionCodes.every((code) => hasPermission(code));
  }
  
  /// عرض زر مع التحقق من الصلاحية
  Widget? buildPermissionButton({
    required String permission,
    required IconData icon,
    required String tooltip,
    required VoidCallback onPressed,
    bool requireAll = false,
    List<String>? additionalPermissions,
  }) {
    final bool hasAccess;
    if (additionalPermissions != null && additionalPermissions.isNotEmpty) {
      hasAccess = requireAll 
          ? hasAllPermissions([permission, ...additionalPermissions])
          : hasAnyPermission([permission, ...additionalPermissions]);
    } else {
      hasAccess = hasPermission(permission);
    }
    
    if (!hasAccess) return null;
    
    return IconButton(
      icon: Icon(icon),
      onPressed: onPressed,
      tooltip: tooltip,
    );
  }
  
  /// عرض قائمة إجراءات مع التحقق من الصلاحيات
  List<Widget> buildPermissionMenuItems(List<Map<String, dynamic>> items) {
    return items.where((item) {
      final String? permission = item['permission'] as String?;
      if (permission == null) return true; // لا يوجد شرط صلاحية
      return hasPermission(permission);
    }).map((item) {
      return ListTile(
        leading: item['icon'] as IconData?,
        title: Text(item['title'] as String),
        onTap: item['onTap'] as VoidCallback?,
        enabled: item['enabled'] as bool? ?? true,
      );
    }).toList();
  }
}

/// widget helper لإخفاء/إظهار العناصر بناءً على الصلاحية
class PermissionBuilder extends StatelessWidget {
  final String permission;
  final List<String>? additionalPermissions;
  final bool requireAll;
  final Widget child;
  final Widget? fallback;
  
  const PermissionBuilder({
    Key? key,
    required this.permission,
    this.additionalPermissions,
    this.requireAll = false,
    required this.child,
    this.fallback,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    final authProvider = AuthProvider.of(context);
    
    final bool hasAccess;
    if (additionalPermissions != null && additionalPermissions.isNotEmpty) {
      hasAccess = requireAll 
          ? additionalPermissions!.every((code) => authProvider.hasPermission(code)) &&
              authProvider.hasPermission(permission)
          : additionalPermissions!.any((code) => authProvider.hasPermission(code)) ||
              authProvider.hasPermission(permission);
    } else {
      hasAccess = authProvider.hasPermission(permission);
    }
    
    return hasAccess ? child : (fallback ?? const SizedBox.shrink());
  }
}

/// enum يحتوي على جميع أكواد الصلاحيات في النظام
class AppPermissions {
  // Sales Module
  static const String salesQuotationCreate = 'sales.quotation.create';
  static const String salesQuotationEdit = 'sales.quotation.edit';
  static const String salesQuotationDelete = 'sales.quotation.delete';
  static const String salesQuotationSend = 'sales.quotation.send';
  static const String salesQuotationAccept = 'sales.quotation.accept';
  static const String salesQuotationReject = 'sales.quotation.reject';
  
  static const String salesOrderCreate = 'sales.order.create';
  static const String salesOrderEdit = 'sales.order.edit';
  static const String salesOrderDelete = 'sales.order.delete';
  static const String salesOrderConfirm = 'sales.order.confirm';
  static const String salesOrderCancel = 'sales.order.cancel';
  
  static const String salesInvoiceCreate = 'sales.invoice.create';
  static const String salesInvoiceEdit = 'sales.invoice.edit';
  static const String salesInvoiceDelete = 'sales.invoice.delete';
  static const String salesInvoicePost = 'sales.invoice.post';
  static const String salesInvoiceCancel = 'sales.invoice.cancel';
  static const String salesInvoiceVoid = 'sales.invoice.void';
  
  static const String salesDeliveryCreate = 'sales.delivery.create';
  static const String salesDeliveryEdit = 'sales.delivery.edit';
  static const String salesDeliveryDelete = 'sales.delivery.delete';
  static const String salesDeliveryConfirm = 'sales.delivery.confirm';
  static const String salesDeliveryCancel = 'sales.delivery.cancel';
  
  // Purchasing Module
  static const String purchaseRFQCreate = 'purchasing.rfq.create';
  static const String purchaseRFQEdit = 'purchasing.rfq.edit';
  static const String purchaseRFQDelete = 'purchasing.rfq.delete';
  static const String purchaseRFQSend = 'purchasing.rfq.send';
  static const String purchaseRFQConvert = 'purchasing.rfq.convert';
  
  static const String purchaseOrderCreate = 'purchasing.order.create';
  static const String purchaseOrderEdit = 'purchasing.order.edit';
  static const String purchaseOrderDelete = 'purchasing.order.delete';
  static const String purchaseOrderConfirm = 'purchasing.order.confirm';
  static const String purchaseOrderCancel = 'purchasing.order.cancel';
  
  static const String purchaseReceiptCreate = 'purchasing.receipt.create';
  static const String purchaseReceiptEdit = 'purchasing.receipt.edit';
  static const String purchaseReceiptDelete = 'purchasing.receipt.delete';
  static const String purchaseReceiptConfirm = 'purchasing.receipt.confirm';
  static const String purchaseReceiptCancel = 'purchasing.receipt.cancel';
  
  static const String purchaseBillCreate = 'purchasing.bill.create';
  static const String purchaseBillEdit = 'purchasing.bill.edit';
  static const String purchaseBillDelete = 'purchasing.bill.delete';
  static const String purchaseBillPost = 'purchasing.bill.post';
  static const String purchaseBillCancel = 'purchasing.bill.cancel';
  
  // Inventory Module
  static const String inventoryItemCreate = 'inventory.item.create';
  static const String inventoryItemEdit = 'inventory.item.edit';
  static const String inventoryItemDelete = 'inventory.item.delete';
  static const String inventoryAdjustmentCreate = 'inventory.adjustment.create';
  static const String inventoryAdjustmentPost = 'inventory.adjustment.post';
  static const String inventoryTransferCreate = 'inventory.transfer.create';
  static const String inventoryTransferConfirm = 'inventory.transfer.confirm';
  
  // Accounting Module
  static const String accountingJournalEntryCreate = 'accounting.journal.create';
  static const String accountingJournalEntryEdit = 'accounting.journal.edit';
  static const String accountingJournalEntryDelete = 'accounting.journal.delete';
  static const String accountingJournalEntryPost = 'accounting.journal.post';
  static const String accountingJournalEntryCancel = 'accounting.journal.cancel';
  
  static const String accountingPeriodOpen = 'accounting.period.open';
  static const String accountingPeriodClose = 'accounting.period.close';
  static const String accountingPeriodReopen = 'accounting.period.reopen';
  
  // Customer Module
  static const String customerCreate = 'customer.create';
  static const String customerEdit = 'customer.edit';
  static const String customerDelete = 'customer.delete';
  static const String customerCreditLimitEdit = 'customer.credit_limit.edit';
  
  // Supplier Module
  static const String supplierCreate = 'supplier.create';
  static const String supplierEdit = 'supplier.edit';
  static const String supplierDelete = 'supplier.delete';
  
  // Payment Module
  static const String paymentReceive = 'payment.receive';
  static const String paymentMake = 'payment.make';
  static const String paymentEdit = 'payment.edit';
  static const String paymentDelete = 'payment.delete';
  static const String paymentVoid = 'payment.void';
  
  // Report Module
  static const String reportView = 'report.view';
  static const String reportExport = 'report.export';
  static const String reportPrint = 'report.print';
  
  // Admin Module
  static const String userCreate = 'user.create';
  static const String userEdit = 'user.edit';
  static const String userDelete = 'user.delete';
  static const String roleCreate = 'role.create';
  static const String roleEdit = 'role.edit';
  static const String roleDelete = 'role.delete';
  static const String permissionAssign = 'permission.assign';
  static const String auditLogView = 'audit.log.view';
  static const String settingsEdit = 'settings.edit';
}
