# core/application/handlers/suppliers/__init__.py
"""Suppliers Handlers - Organized by use case"""

from .create_supplier_handler import CreateSupplierHandler
from .update_supplier_handler import UpdateSupplierHandler
from .change_supplier_status_handler import ChangeSupplierStatusHandler
from .delete_supplier_handler import DeleteSupplierHandler
from .get_supplier_query_handler import GetSupplierQueryHandler
from .list_suppliers_query_handler import ListSuppliersQueryHandler
from .search_suppliers_query_handler import SearchSuppliersQueryHandler  # ✅ إضافة
from .get_supplier_statement_query_handler import GetSupplierStatementQueryHandler  # ✅ إضافة

__all__ = [
    "CreateSupplierHandler",
    "UpdateSupplierHandler",
    "ChangeSupplierStatusHandler",
    "DeleteSupplierHandler",
    "GetSupplierQueryHandler",
    "ListSuppliersQueryHandler",
    "SearchSuppliersQueryHandler",  # ✅ إضافة
    "GetSupplierStatementQueryHandler",  # ✅ إضافة
]