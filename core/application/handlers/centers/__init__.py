# core/application/handlers/centers/__init__.py
"""
Centers Handlers - معالجات مراكز التكلفة والربح

هذا المجلد يحتوي على جميع معالجات مراكز التكلفة والربح
(Commands و Queries) مقسمة حسب الوظيفة.
"""

from .create_center_handler import CreateCenterHandler
from .update_center_handler import UpdateCenterHandler
from .activate_center_handler import ActivateCenterHandler
from .suspend_center_handler import SuspendCenterHandler
from .close_center_handler import CloseCenterHandler
from .delete_center_handler import DeleteCenterHandler
from .get_center_handler import GetCenterHandler
from .list_centers_handler import ListCentersHandler
from .get_center_tree_handler import GetCenterTreeHandler
from .create_allocation_handler import CreateAllocationHandler
from .post_allocation_handler import PostAllocationHandler
from .get_center_summary_handler import GetCenterSummaryHandler
__all__ = [
    # Command Handlers
    "CreateCenterHandler",
    "UpdateCenterHandler",
    "ActivateCenterHandler",
    "SuspendCenterHandler",
    "CloseCenterHandler",
    "DeleteCenterHandler",
    "CreateAllocationHandler",
    "PostAllocationHandler",
    
    # Query Handlers
    "GetCenterHandler",
    "ListCentersHandler",
    "GetCenterTreeHandler",
]