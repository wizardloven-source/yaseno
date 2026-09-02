# core/application/handlers/purchasing/__init__.py
"""
Purchasing Handlers - معالجات المشتريات
"""

from .create_purchase_order_handler import CreatePurchaseOrderHandler
from .add_purchase_line_handler import AddPurchaseLineHandler
from .update_purchase_line_handler import UpdatePurchaseLineHandler
from .remove_purchase_line_handler import RemovePurchaseLineHandler
from .clear_purchase_lines_handler import ClearPurchaseLinesHandler

# ✅ معالجات محدثة
from .post_purchase_order_handler import PostPurchaseOrderHandler
from .delete_draft_purchase_order_handler import DeleteDraftPurchaseOrderHandler

# ✅ معالجات محدثة لدعم المخزون
from .receive_purchase_line_handler import ReceivePurchaseLineHandler

# ✅ معالج جديد
from .receive_purchase_order_handler import ReceivePurchaseOrderHandler

# ✅ معالجات الاستعلام
from .get_purchase_order_query_handler import GetPurchaseOrderQueryHandler
from .list_purchase_orders_query_handler import ListPurchaseOrdersQueryHandler

# ✅ معالج جديد لجلب أوامر شراء المورد
from .get_supplier_orders_query_handler import GetSupplierOrdersQueryHandler


__all__ = [
    # Command Handlers
    "CreatePurchaseOrderHandler",
    "AddPurchaseLineHandler",
    "UpdatePurchaseLineHandler",
    "RemovePurchaseLineHandler",
    "ClearPurchaseLinesHandler",
    "PostPurchaseOrderHandler",
    "DeleteDraftPurchaseOrderHandler",
    
    # ✅ Receive Handlers (محدثة)
    "ReceivePurchaseLineHandler",
    "ReceivePurchaseOrderHandler",  # ✅ جديد
    
    # Query Handlers
    "GetPurchaseOrderQueryHandler",
    "ListPurchaseOrdersQueryHandler",
    "GetSupplierOrdersQueryHandler",  # ✅ جديد
]