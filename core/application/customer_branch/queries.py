# core/application/customer_branch/queries.py
"""
Customer Branch Queries - استعلامات فروع العملاء
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GetBranchQuery:
    """استعلام لجلب فرع بواسطة المعرف"""
    branch_id: str


@dataclass(frozen=True)
class GetBranchByCodeQuery:
    """استعلام لجلب فرع بواسطة الكود"""
    code: str


@dataclass(frozen=True)
class GetDefaultBranchQuery:
    """استعلام لجلب الفرع الافتراضي لعميل"""
    customer_id: str


@dataclass(frozen=True)
class ListBranchesQuery:
    """استعلام لقائمة فروع العملاء"""
    customer_id: Optional[str] = None
    status: Optional[str] = None
    include_deleted: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class SearchBranchesQuery:
    """استعلام للبحث عن فروع"""
    search_text: str
    customer_id: Optional[str] = None
    limit: int = 50
    offset: int = 0