# C:\Users\MTC\Desktop\erpya\core\application\handlers\customers\__init__.py
"""Customers Handlers - Organized by use case"""

from .create_customer_handler import CreateCustomerHandler
from .update_customer_handler import UpdateCustomerHandler
from .change_customer_status_handler import ChangeCustomerStatusHandler
from .delete_customer_handler import DeleteCustomerHandler
from .get_customer_query_handler import GetCustomerQueryHandler
from .list_customers_query_handler import ListCustomersQueryHandler

# ✅ إضافة المعالجات المفقودة
from .search_customers_query_handler import SearchCustomersQueryHandler
from .get_customer_statement_query_handler import GetCustomerStatementQueryHandler

__all__ = [
    "CreateCustomerHandler",
    "UpdateCustomerHandler",
    "ChangeCustomerStatusHandler",
    "DeleteCustomerHandler",
    "GetCustomerQueryHandler",
    "ListCustomersQueryHandler",
    "SearchCustomersQueryHandler",      # ✅ إضافة
    "GetCustomerStatementQueryHandler", # ✅ إضافة
]