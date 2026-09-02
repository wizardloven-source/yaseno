# core/application/customer_branch/__init__.py
"""
Customer Branch Application - طبقة تطبيق فروع العملاء
"""

from .commands import (
    CreateBranchCommand,
    UpdateBranchCommand,
    DeleteBranchCommand,
    ActivateBranchCommand,
    DeactivateBranchCommand,
    SetDefaultBranchCommand,
)
from .queries import (
    GetBranchQuery,
    GetBranchByCodeQuery,
    GetDefaultBranchQuery,
    ListBranchesQuery,
    SearchBranchesQuery,
)
from .dtos import (
    CustomerBranchDTO,
    BranchAddressDTO,
    BranchContactDTO,
    BranchGeoLocationDTO,
    CreateBranchDTO,
    UpdateBranchDTO,
    BranchListDTO,
)
from .converters import (
    branch_to_dto,
    dto_to_branch,
    branches_to_dto_list,
)

__all__ = [
    # Commands
    "CreateBranchCommand",
    "UpdateBranchCommand",
    "DeleteBranchCommand",
    "ActivateBranchCommand",
    "DeactivateBranchCommand",
    "SetDefaultBranchCommand",
    
    # Queries
    "GetBranchQuery",
    "GetBranchByCodeQuery",
    "GetDefaultBranchQuery",
    "ListBranchesQuery",
    "SearchBranchesQuery",
    
    # DTOs
    "CustomerBranchDTO",
    "BranchAddressDTO",
    "BranchContactDTO",
    "BranchGeoLocationDTO",
    "CreateBranchDTO",
    "UpdateBranchDTO",
    "BranchListDTO",
    
    # Converters
    "branch_to_dto",
    "dto_to_branch",
    "branches_to_dto_list",
]