# core/bootstrap/modules/workflow.py
"""
وحدة سير العمل - تسجيل جميع خدمات سير العمل والموافقات
مستخرجة من bootstrap.py
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module, lazy_event_handler

logger = logging.getLogger(__name__)


class WorkflowModule(Module):
    """
    وحدة سير العمل - نظام الموافقات المتقدم
    
    تشمل:
        1. إنشاء سير العمل (Workflow)
        2. خطوات الموافقة (Approval Steps)
        3. طلبات الموافقة (Approval Requests)
        4. الموافقة/الرفض (Approve/Reject)
        5. تصعيد الطلبات (Escalation)
        6. إلغاء الطلبات (Cancellation)
        7. إشعارات الموافقات
        8. صلاحيات الموافقة
        9. الموافقة التلقائية (Auto-approve)
        10. مهلة الموافقة (Timeout)
        
    أنواع سير العمل المدعومة:
        1. فواتير (Invoices)
        2. دفعات (Payments)
        3. قيود محاسبية (Journal Entries)
        4. أوامر شراء (Purchase Orders)
        5. أوامر مبيعات (Sales Orders)
        6. مصروفات (Expenses)
        7. ميزانيات (Budgets)
        8. عقود (Contracts)
        9. مستخدمين (Users)
    """
    
    name = "workflow"
    description = "نظام سير العمل والموافقات - إدارة الموافقات المتقدمة"
    dependencies = ["database", "security", "notifications"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات سير العمل"""
        
        # ========== Repositories ==========
        container.register(
            "workflow_repo",
            "core.infrastructure.db.postgres.workflow_repository.PostgresWorkflowRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        container.register(
            "approval_request_repo",
            "core.infrastructure.db.postgres.workflow_repository.PostgresApprovalRequestRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== Domain Services ==========
        container.register(
            "workflow_service",
            "core.domain.workflow.services.WorkflowService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["workflow_repo", "approval_request_repo"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_workflow_handler",
            "core.application.handlers.workflow.CreateWorkflowHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_workflow_handler",
            "core.application.handlers.workflow.UpdateWorkflowHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "activate_workflow_handler",
            "core.application.handlers.workflow.ActivateWorkflowHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "deactivate_workflow_handler",
            "core.application.handlers.workflow.DeactivateWorkflowHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_workflow_handler",
            "core.application.handlers.workflow.DeleteWorkflowHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # إدارة طلبات الموافقة
        container.register(
            "create_approval_request_handler",
            "core.application.handlers.workflow.CreateApprovalRequestHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "submit_approval_request_handler",
            "core.application.handlers.workflow.SubmitApprovalRequestHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "approve_request_handler",
            "core.application.handlers.workflow.ApproveRequestHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "reject_request_handler",
            "core.application.handlers.workflow.RejectRequestHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "cancel_request_handler",
            "core.application.handlers.workflow.CancelRequestHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "escalate_request_handler",
            "core.application.handlers.workflow.EscalateRequestHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "reassign_request_handler",
            "core.application.handlers.workflow.ReassignRequestHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # الموافقات الجماعية
        container.register(
            "batch_approve_requests_handler",
            "core.application.handlers.workflow.BatchApproveRequestsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "batch_reject_requests_handler",
            "core.application.handlers.workflow.BatchRejectRequestsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_workflow_handler",
            "core.application.handlers.workflow.GetWorkflowQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["workflow_repo"]
        )
        container.register(
            "list_workflows_handler",
            "core.application.handlers.workflow.ListWorkflowsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["workflow_repo"]
        )
        container.register(
            "get_workflow_by_entity_handler",
            "core.application.handlers.workflow.GetWorkflowByEntityQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["workflow_repo"]
        )
        
        container.register(
            "get_approval_request_handler",
            "core.application.handlers.workflow.GetApprovalRequestQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["approval_request_repo"]
        )
        container.register(
            "list_approval_requests_handler",
            "core.application.handlers.workflow.ListApprovalRequestsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["approval_request_repo"]
        )
        container.register(
            "list_pending_requests_handler",
            "core.application.handlers.workflow.list_pending_requests_query_handler.ListPendingRequestsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["approval_request_repo"]
        )
        container.register(
            "list_requests_by_approver_handler",
            "core.application.handlers.workflow.ListRequestsByApproverQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["approval_request_repo"]
        )
        container.register(
            "list_requests_by_requestor_handler",
            "core.application.handlers.workflow.ListRequestsByRequestorQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["approval_request_repo"]
        )
        container.register(
            "get_request_statistics_handler",
            "core.application.handlers.workflow.GetRequestStatisticsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["approval_request_repo"]
        )
        container.register(
            "get_request_by_entity_handler",
            "core.application.handlers.workflow.GetRequestByEntityQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["approval_request_repo"]
        )
        
        # ========== Event Handlers ==========
        container.register(
            "request_submitted_event_handler",
            "core.application.handlers.workflow.RequestSubmittedEventHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "request_approved_event_handler",
            "core.application.handlers.workflow.RequestApprovedEventHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "request_rejected_event_handler",
            "core.application.handlers.workflow.RequestRejectedEventHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "request_escalated_event_handler",
            "core.application.handlers.workflow.RequestEscalatedEventHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "notification_service"]
        )
        container.register(
            "request_timeout_handler",
            "core.application.handlers.workflow.RequestTimeoutHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "workflow_service", "notification_service"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus و Event Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        event_bus = container.resolve("event_bus")
        
        # ✅ استخدام نطاق (scope) لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ✅ الحصول على uow وفتح الجلسة
            uow = scoped_container.resolve("uow")
            
            # ========== Command Handlers ==========
            # ✅ جميع Command Handlers داخل with uow
            with uow:
                # إدارة سير العمل
                try:
                    command_bus.register("CreateWorkflowCommand", "create_workflow_handler")
                    logger.info("✅ Registered CreateWorkflowCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register CreateWorkflowCommand: {e}")
                
                try:
                    command_bus.register("UpdateWorkflowCommand", "update_workflow_handler")
                    logger.info("✅ Registered UpdateWorkflowCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register UpdateWorkflowCommand: {e}")
                
                try:
                    command_bus.register("ActivateWorkflowCommand", "activate_workflow_handler")
                    logger.info("✅ Registered ActivateWorkflowCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register ActivateWorkflowCommand: {e}")
                
                try:
                    command_bus.register("DeactivateWorkflowCommand", "deactivate_workflow_handler")
                    logger.info("✅ Registered DeactivateWorkflowCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register DeactivateWorkflowCommand: {e}")
                
                try:
                    command_bus.register("DeleteWorkflowCommand", "delete_workflow_handler")
                    logger.info("✅ Registered DeleteWorkflowCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register DeleteWorkflowCommand: {e}")
                
                # إدارة طلبات الموافقة
                try:
                    command_bus.register("CreateApprovalRequestCommand", "create_approval_request_handler")
                    logger.info("✅ Registered CreateApprovalRequestCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register CreateApprovalRequestCommand: {e}")
                
                try:
                    command_bus.register("SubmitRequestCommand", "submit_approval_request_handler")
                    logger.info("✅ Registered SubmitRequestCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register SubmitRequestCommand: {e}")
                
                try:
                    command_bus.register("ApproveRequestCommand", "approve_request_handler")
                    logger.info("✅ Registered ApproveRequestCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register ApproveRequestCommand: {e}")
                
                try:
                    command_bus.register("RejectRequestCommand", "reject_request_handler")
                    logger.info("✅ Registered RejectRequestCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register RejectRequestCommand: {e}")
                
                try:
                    command_bus.register("CancelRequestCommand", "cancel_request_handler")
                    logger.info("✅ Registered CancelRequestCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register CancelRequestCommand: {e}")
                
                try:
                    command_bus.register("EscalateRequestCommand", "escalate_request_handler")
                    logger.info("✅ Registered EscalateRequestCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register EscalateRequestCommand: {e}")
                
                try:
                    command_bus.register("ReassignRequestCommand", "reassign_request_handler")
                    logger.info("✅ Registered ReassignRequestCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register ReassignRequestCommand: {e}")
                
                # الموافقات الجماعية
                try:
                    command_bus.register("BatchApproveRequestsCommand", "batch_approve_requests_handler")
                    logger.info("✅ Registered BatchApproveRequestsCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register BatchApproveRequestsCommand: {e}")
                
                try:
                    command_bus.register("BatchRejectRequestsCommand", "batch_reject_requests_handler")
                    logger.info("✅ Registered BatchRejectRequestsCommand")
                except Exception as e:
                    logger.error(f"❌ Failed to register BatchRejectRequestsCommand: {e}")
            
            # ========== Query Handlers ==========
            # ✅ Query Handlers تعتمد على repositories وليس uow
            try:
                query_bus.register("GetWorkflowQuery", "get_workflow_handler")
                logger.info("✅ Registered GetWorkflowQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetWorkflowQuery: {e}")
            
            try:
                query_bus.register("ListWorkflowsQuery", "list_workflows_handler")
                logger.info("✅ Registered ListWorkflowsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListWorkflowsQuery: {e}")
            
            try:
                query_bus.register("GetWorkflowByEntityQuery", "get_workflow_by_entity_handler")
                logger.info("✅ Registered GetWorkflowByEntityQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetWorkflowByEntityQuery: {e}")
            
            try:
                query_bus.register("GetRequestQuery", "get_approval_request_handler")
                logger.info("✅ Registered GetRequestQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetRequestQuery: {e}")
            
            try:
                query_bus.register("ListRequestsQuery", "list_approval_requests_handler")
                logger.info("✅ Registered ListRequestsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListRequestsQuery: {e}")
            
            try:
                query_bus.register("ListPendingRequestsQuery", "list_pending_requests_handler")
                logger.info("✅ Registered ListPendingRequestsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListPendingRequestsQuery: {e}")
            
            try:
                query_bus.register("GetRequestsByApproverQuery", "list_requests_by_approver_handler")
                logger.info("✅ Registered GetRequestsByApproverQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetRequestsByApproverQuery: {e}")
            
            try:
                query_bus.register("GetRequestsByRequestorQuery", "list_requests_by_requestor_handler")
                logger.info("✅ Registered GetRequestsByRequestorQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetRequestsByRequestorQuery: {e}")
            
            try:
                query_bus.register("GetRequestStatisticsQuery", "get_request_statistics_handler")
                logger.info("✅ Registered GetRequestStatisticsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetRequestStatisticsQuery: {e}")
            
            try:
                query_bus.register("GetRequestByEntityQuery", "get_request_by_entity_handler")
                logger.info("✅ Registered GetRequestByEntityQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetRequestByEntityQuery: {e}")
            
            # ========== Event Handlers ==========
            # ✅ Event Handlers تُحل في نطاق جديد (جلسة جديدة) لكل حدث
            try:
                event_bus.add_handler("RequestSubmittedEvent", lazy_event_handler(scoped_container, "request_submitted_event_handler"))
                logger.info("✅ Registered RequestSubmittedEventHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register RequestSubmittedEventHandler: {e}")
            
            try:
                event_bus.add_handler("RequestApprovedEvent", lazy_event_handler(scoped_container, "request_approved_event_handler"))
                logger.info("✅ Registered RequestApprovedEventHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register RequestApprovedEventHandler: {e}")
            
            try:
                event_bus.add_handler("RequestRejectedEvent", lazy_event_handler(scoped_container, "request_rejected_event_handler"))
                logger.info("✅ Registered RequestRejectedEventHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register RequestRejectedEventHandler: {e}")
            
            try:
                event_bus.add_handler("RequestEscalatedEvent", lazy_event_handler(scoped_container, "request_escalated_event_handler"))
                logger.info("✅ Registered RequestEscalatedEventHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register RequestEscalatedEventHandler: {e}")
            
            try:
                event_bus.add_handler("RequestExpiredEvent", lazy_event_handler(scoped_container, "request_timeout_handler"))
                logger.info("✅ Registered RequestTimeoutHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register RequestTimeoutHandler: {e}")
        
        # ========== تشغيل مهام الخلفية ==========
        # self._setup_background_tasks()
    
    def _setup_background_tasks(self) -> None:
        """إعداد مهام الخلفية لسير العمل"""
        pass