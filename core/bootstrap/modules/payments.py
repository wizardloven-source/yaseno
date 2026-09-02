# core/bootstrap/modules/payments.py
"""
وحدة الدفعات - تسجيل جميع خدمات الدفعات
✅ محدث: إضافة دعم فروع العملاء (Customer Branches)
مستخرجة من bootstrap.py
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module, lazy_event_handler

logger = logging.getLogger(__name__)


class PaymentsModule(Module):
    """
    وحدة الدفعات
    
    تشمل:
        1. قبض (Receive) - استلام مبلغ من عميل
        2. دفع (Pay) - دفع مبلغ لمورد
        3. تحويل (Transfer) - تحويل بين الصناديق
        4. إدارة الدفعات الجزئية
        5. ربط الدفعات بالفواتير
        6. ✅ دعم فروع العملاء (جديد)
    """
    
    name = "payments"
    description = "إدارة الدفعات - قبض، دفع، تحويل، ومقاصة مع دعم فروع العملاء"
    dependencies = ["database", "accounting", "funds", "customers", "suppliers", "invoicing"]
    version = "2.1.0"  # ✅ تحديث الإصدار
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الدفعات"""
        
        # ========== Repositories ==========
        # ✅ جميع الـ Repositories تحتاج إلى session
        container.register(
            "payment_repo",
            "core.infrastructure.db.postgres.repositories_payment.PostgresPaymentRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        container.register(
            "payment_line_repo",
            "core.infrastructure.db.postgres.repositories_payment.PostgresPaymentLineRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        container.register(
            "payment_allocation_repo",
            "core.infrastructure.db.postgres.repositories_payment.PostgresPaymentAllocationRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== Services ==========
        container.register(
            "payment_service",
            "core.application.payments.services.PaymentService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["payment_repo", "uow"]
        )
        container.register(
            "payment_allocation_service",
            "core.application.payments.services.PaymentAllocationService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["payment_allocation_repo", "invoice_repo", "uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_payment_handler",
            "core.application.handlers.payments.CreatePaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_payment_handler",
            "core.application.handlers.payments.UpdatePaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "add_payment_line_handler",
            "core.application.handlers.payments.AddPaymentLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "remove_payment_line_handler",
            "core.application.handlers.payments.RemovePaymentLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "approve_payment_handler",
            "core.application.handlers.payments.ApprovePaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "reject_payment_handler",
            "core.application.handlers.payments.RejectPaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "complete_payment_handler",
            "core.application.handlers.payments.CompletePaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "accounting_orchestrator", "posting_engine", "payment_allocation_service"]
        )
        container.register(
            "cancel_payment_handler",
            "core.application.handlers.payments.CancelPaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "posting_engine"]
        )
        container.register(
            "delete_draft_payment_handler",
            "core.application.handlers.payments.DeleteDraftPaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "allocate_payment_handler",
            "core.application.handlers.payments.AllocatePaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "payment_allocation_service"]
        )
        container.register(
            "reverse_allocation_handler",
            "core.application.handlers.payments.ReverseAllocationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "payment_allocation_service", "posting_engine"]
        )
        
        # ========== ✅ Customer Branch Payment Command Handlers (جديد) ==========
        # Customer-branch payment support is not implemented in this workspace yet,
        # so the bootstrap registers only the handlers that are actually available.
        container.register(
            "update_payment_branch_handler",
            "core.application.handlers.payments.update_payment_handler.UpdatePaymentHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Event Handlers ==========
        container.register(
            "payment_completed_event_handler",
            "core.application.handlers.payments.PaymentCompletedEventHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "posting_engine"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_payment_handler",
            "core.application.handlers.payments.GetPaymentQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["payment_repo"]
        )
        container.register(
            "list_payments_handler",
            "core.application.handlers.payments.ListPaymentsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["payment_repo"]
        )
        container.register(
            "get_payment_summary_handler",
            "core.application.handlers.payments.GetPaymentSummaryQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["payment_repo"]
        )
        container.register(
            "get_customer_payments_handler",
            "core.application.handlers.payments.GetCustomerPaymentsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["payment_repo"]
        )
        container.register(
            "get_supplier_payments_handler",
            "core.application.handlers.payments.GetSupplierPaymentsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["payment_repo"]
        )
        
        # ========== ✅ Customer Branch Payment Query Handlers (جديد) ==========
        container.register(
            "get_customer_branch_payments_handler",
            "core.application.handlers.payments.get_customer_payments_query_handler.GetCustomerPaymentsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["payment_repo"]
        )
        container.register(
            "get_payment_branch_statistics_handler",
            "core.application.handlers.payments.get_payment_statistics_query_handler.GetPaymentStatisticsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["payment_repo"]
        )
        
        container.register(
            "get_payment_allocations_handler",
            "core.application.handlers.payments.GetPaymentAllocationsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["payment_allocation_repo"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreatePaymentCommand", "create_payment_handler")
                logger.info("✅ Registered CreatePaymentCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreatePaymentCommand: {e}")
            
            try:
                command_bus.register("UpdatePaymentCommand", "update_payment_handler")
                logger.info("✅ Registered UpdatePaymentCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdatePaymentCommand: {e}")
            
            try:
                command_bus.register("AddPaymentLineCommand", "add_payment_line_handler")
                logger.info("✅ Registered AddPaymentLineCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register AddPaymentLineCommand: {e}")
            
            try:
                command_bus.register("RemovePaymentLineCommand", "remove_payment_line_handler")
                logger.info("✅ Registered RemovePaymentLineCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register RemovePaymentLineCommand: {e}")
            
            try:
                command_bus.register("ApprovePaymentCommand", "approve_payment_handler")
                logger.info("✅ Registered ApprovePaymentCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ApprovePaymentCommand: {e}")
            
            try:
                command_bus.register("RejectPaymentCommand", "reject_payment_handler")
                logger.info("✅ Registered RejectPaymentCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register RejectPaymentCommand: {e}")
            
            try:
                command_bus.register("CompletePaymentCommand", "complete_payment_handler")
                logger.info("✅ Registered CompletePaymentCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CompletePaymentCommand: {e}")
            
            try:
                command_bus.register("CancelPaymentCommand", "cancel_payment_handler")
                logger.info("✅ Registered CancelPaymentCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CancelPaymentCommand: {e}")
            
            try:
                command_bus.register("DeleteDraftPaymentCommand", "delete_draft_payment_handler")
                logger.info("✅ Registered DeleteDraftPaymentCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteDraftPaymentCommand: {e}")
            
            try:
                command_bus.register("AllocatePaymentCommand", "allocate_payment_handler")
                logger.info("✅ Registered AllocatePaymentCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register AllocatePaymentCommand: {e}")
            
            try:
                command_bus.register("ReverseAllocationCommand", "reverse_allocation_handler")
                logger.info("✅ Registered ReverseAllocationCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ReverseAllocationCommand: {e}")
            
            # ========== ✅ Customer Branch Payment Command Handlers (جديد) ==========
            try:
                command_bus.register("UpdatePaymentBranchCommand", "update_payment_branch_handler")
                logger.info("✅ Registered UpdatePaymentBranchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdatePaymentBranchCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetPaymentQuery", "get_payment_handler")
                logger.info("✅ Registered GetPaymentQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetPaymentQuery: {e}")
            
            try:
                query_bus.register("ListPaymentsQuery", "list_payments_handler")
                logger.info("✅ Registered ListPaymentsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListPaymentsQuery: {e}")
            
            try:
                query_bus.register("GetPaymentSummaryQuery", "get_payment_summary_handler")
                logger.info("✅ Registered GetPaymentSummaryQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetPaymentSummaryQuery: {e}")
            
            try:
                query_bus.register("GetCustomerPaymentsQuery", "get_customer_payments_handler")
                logger.info("✅ Registered GetCustomerPaymentsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCustomerPaymentsQuery: {e}")
            
            try:
                query_bus.register("GetSupplierPaymentsQuery", "get_supplier_payments_handler")
                logger.info("✅ Registered GetSupplierPaymentsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSupplierPaymentsQuery: {e}")
            
            # ========== ✅ Customer Branch Payment Query Handlers (جديد) ==========
            try:
                query_bus.register("GetCustomerBranchPaymentsQuery", "get_customer_branch_payments_handler")
                logger.info("✅ Registered GetCustomerBranchPaymentsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCustomerBranchPaymentsQuery: {e}")
            
            try:
                query_bus.register("GetPaymentBranchStatisticsQuery", "get_payment_branch_statistics_handler")
                logger.info("✅ Registered GetPaymentBranchStatisticsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetPaymentBranchStatisticsQuery: {e}")
            
            try:
                query_bus.register("GetPaymentAllocationsQuery", "get_payment_allocations_handler")
                logger.info("✅ Registered GetPaymentAllocationsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetPaymentAllocationsQuery: {e}")
            
            # ========== Event Handlers ==========
            try:
                event_bus = container.resolve("event_bus")
                event_bus.add_handler("PaymentCompletedEvent", lazy_event_handler(scoped_container, "payment_completed_event_handler"))
                logger.info("✅ Registered PaymentCompletedEventHandler")
            except Exception as e:
                logger.error(f"❌ Failed to register PaymentCompletedEventHandler: {e}")