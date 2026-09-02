# core/application/handlers/workflow/__init__.py
"""
Workflow Handlers - معالجات سير عمل الموافقات
"""

from .create_workflow_handler import CreateWorkflowHandler
from .update_workflow_handler import UpdateWorkflowHandler
from .activate_workflow_handler import ActivateWorkflowHandler
from .deactivate_workflow_handler import DeactivateWorkflowHandler
from .delete_workflow_handler import DeleteWorkflowHandler

from .create_request_handler import CreateRequestHandler
from .create_approval_request_handler import CreateApprovalRequestHandler
from .submit_approval_request_handler import SubmitApprovalRequestHandler
from .approve_request_handler import ApproveRequestHandler
from .reject_request_handler import RejectRequestHandler
from .cancel_request_handler import CancelRequestHandler
from .escalate_request_handler import EscalateRequestHandler
from .reassign_request_handler import ReassignRequestHandler

from .batch_approve_requests_handler import BatchApproveRequestsHandler
from .batch_reject_requests_handler import BatchRejectRequestsHandler

# ✅ Query Handlers
from .get_request_handler import GetRequestHandler
from .list_requests_handler import ListRequestsHandler
from .list_pending_requests_handler import ListPendingRequestsHandler
from .get_workflow_query_handler import GetWorkflowQueryHandler              # ✅ إضافة
from .list_workflows_query_handler import ListWorkflowsQueryHandler          # ✅ إضافة
from .get_workflow_by_entity_query_handler import GetWorkflowByEntityQueryHandler  # ✅ إضافة
from .get_approval_request_query_handler import GetApprovalRequestQueryHandler      # ✅ إضافة
from .list_approval_requests_query_handler import ListApprovalRequestsQueryHandler  # ✅ إضافة
from .list_requests_by_approver_query_handler import ListRequestsByApproverQueryHandler  # ✅ إضافة
from .list_requests_by_requestor_query_handler import ListRequestsByRequestorQueryHandler  # ✅ إضافة
from .get_request_statistics_query_handler import GetRequestStatisticsQueryHandler  # ✅ إضافة
from .get_request_by_entity_query_handler import GetRequestByEntityQueryHandler  # ✅ إضافة

# ✅ Event Handlers
from .request_submitted_event_handler import RequestSubmittedEventHandler
from .request_approved_event_handler import RequestApprovedEventHandler
from .request_rejected_event_handler import RequestRejectedEventHandler
from .request_escalated_event_handler import RequestEscalatedEventHandler
from .request_timeout_handler import RequestTimeoutHandler


__all__ = [
    # Workflow Command Handlers
    "CreateWorkflowHandler",
    "UpdateWorkflowHandler",
    "ActivateWorkflowHandler",
    "DeactivateWorkflowHandler",
    "DeleteWorkflowHandler",
    
    # Request Command Handlers
    "CreateRequestHandler",
    "CreateApprovalRequestHandler",
    "SubmitApprovalRequestHandler",
    "ApproveRequestHandler",
    "RejectRequestHandler",
    "CancelRequestHandler",
    "EscalateRequestHandler",
    "ReassignRequestHandler",
    
    # Batch Handlers
    "BatchApproveRequestsHandler",
    "BatchRejectRequestsHandler",
    
    # Query Handlers
    "GetRequestHandler",
    "ListRequestsHandler",
    "ListPendingRequestsHandler",
    "GetWorkflowQueryHandler",              # ✅ إضافة
    "ListWorkflowsQueryHandler",            # ✅ إضافة
    "GetWorkflowByEntityQueryHandler",      # ✅ إضافة
    "GetApprovalRequestQueryHandler",       # ✅ إضافة
    "ListApprovalRequestsQueryHandler",     # ✅ إضافة
    "ListRequestsByApproverQueryHandler",   # ✅ إضافة
    "ListRequestsByRequestorQueryHandler",  # ✅ إضافة
    "GetRequestStatisticsQueryHandler",     # ✅ إضافة
    "GetRequestByEntityQueryHandler",       # ✅ إضافة
    
    # Event Handlers
    "RequestSubmittedEventHandler",
    "RequestApprovedEventHandler",
    "RequestRejectedEventHandler",
    "RequestEscalatedEventHandler",
    "RequestTimeoutHandler",
]