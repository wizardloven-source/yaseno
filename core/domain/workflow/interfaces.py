# core/domain/workflow/interfaces.py
"""
Approval Workflow Repository Interfaces - واجهات مستودع سير عمل الموافقات
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime

from .entities import Workflow, ApprovalRequest
from .value_objects import (
    WorkflowId, RequestId, WorkflowStatus,
    RequestStatus, WorkflowEntityType
)


class IWorkflowRepository(ABC):
    """واجهة مستودع سير العمل"""

    @abstractmethod
    def save(self, workflow: Workflow) -> None:
        """حفظ سير العمل"""
        pass

    @abstractmethod
    def get_by_id(self, workflow_id: WorkflowId) -> Optional[Workflow]:
        """الحصول على سير عمل بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Workflow]:
        """الحصول على سير عمل بواسطة الكود"""
        pass

    @abstractmethod
    def get_by_entity_type(self, entity_type: WorkflowEntityType) -> Optional[Workflow]:
        """الحصول على سير عمل لنوع كيان معين"""
        pass

    @abstractmethod
    def list_all(
        self,
        entity_type: Optional[WorkflowEntityType] = None,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Workflow]:
        """قائمة سير العمل"""
        pass

    @abstractmethod
    def delete(self, workflow_id: WorkflowId) -> bool:
        """حذف سير العمل"""
        pass


class IApprovalRequestRepository(ABC):
    """واجهة مستودع طلبات الموافقة"""

    @abstractmethod
    def save(self, request: ApprovalRequest) -> None:
        """حفظ طلب الموافقة"""
        pass

    @abstractmethod
    def get_by_id(self, request_id: RequestId) -> Optional[ApprovalRequest]:
        """الحصول على طلب بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_entity(self, entity_type: WorkflowEntityType, entity_id: str) -> Optional[ApprovalRequest]:
        """الحصول على طلب لكيان معين"""
        pass

    @abstractmethod
    def list_by_entity_type(
        self,
        entity_type: WorkflowEntityType,
        status: Optional[RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة طلبات حسب نوع الكيان"""
        pass

    @abstractmethod
    def list_by_approver(
        self,
        approver_id: str,
        status: Optional[RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة طلبات مراجعة من قبل مستخدم معين"""
        pass

    @abstractmethod
    def list_by_requestor(
        self,
        requestor_id: str,
        status: Optional[RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة طلبات مقدم من قبل مستخدم معين"""
        pass

    @abstractmethod
    def list_pending(
        self,
        entity_type: Optional[WorkflowEntityType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة الطلبات المعلقة"""
        pass

    @abstractmethod
    def list_by_date_range(
        self,
        from_date: datetime,
        to_date: datetime,
        status: Optional[RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة طلبات في نطاق زمني"""
        pass

    @abstractmethod
    def count_by_status(self, status: RequestStatus) -> int:
        """حساب عدد الطلبات حسب الحالة"""
        pass

    @abstractmethod
    def delete(self, request_id: RequestId) -> bool:
        """حذف طلب (فقط إذا كان مسودة)"""
        pass