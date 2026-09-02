# core/bootstrap/modules/customers.py
"""
وحدة العملاء - تسجيل جميع خدمات العملاء
✅ محدث: إضافة دعم فروع العملاء (Customer Branches)
مستخرجة من bootstrap.py
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class CustomersModule(Module):
    """وحدة العملاء - إدارة العملاء والمجموعات وفروع العملاء"""
    
    name = "customers"
    description = "إدارة العملاء، المجموعات، الائتمان، فروع العملاء، وتاريخ المعاملات"
    dependencies = ["database"]
    version = "2.1.0"  # ✅ تحديث الإصدار
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات العملاء"""
        
        # ========== Customer Repository ==========
        container.register(
            "customer_repo",
            "core.infrastructure.db.postgres.customers_repository.PostgresCustomerRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== ✅ Customer Branch Repository (جديد) ==========
        container.register(
            "customer_branch_repo",
            "core.infrastructure.db.postgres.customer_branch_repository.PostgresCustomerBranchRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== Services ==========
        container.register(
            "customer_service",
            "core.application.customers.services.CustomerService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["customer_repo", "uow"]
        )
        
        # ========== ✅ Customer Branch Service (جديد) ==========
        container.register(
            "customer_branch_service",
            "core.application.customer_branch.services.CustomerBranchService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["customer_branch_repo"]
        )
        
        # ========== Customer Command Handlers ==========
        container.register(
            "create_customer_handler",
            "core.application.handlers.customers.CreateCustomerHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_customer_handler",
            "core.application.handlers.customers.UpdateCustomerHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "change_customer_status_handler",
            "core.application.handlers.customers.ChangeCustomerStatusHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_customer_handler",
            "core.application.handlers.customers.DeleteCustomerHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== ✅ Customer Branch Command Handlers (جديد) ==========
        container.register(
            "create_branch_handler",
            "core.application.handlers.customer_branch.CreateBranchHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_branch_handler",
            "core.application.handlers.customer_branch.UpdateBranchHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_branch_handler",
            "core.application.handlers.customer_branch.DeleteBranchHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "activate_branch_handler",
            "core.application.handlers.customer_branch.ActivateBranchHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "deactivate_branch_handler",
            "core.application.handlers.customer_branch.DeactivateBranchHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "set_default_branch_handler",
            "core.application.handlers.customer_branch.SetDefaultBranchHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Customer Query Handlers ==========
        container.register(
            "get_customer_handler",
            "core.application.handlers.customers.GetCustomerQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["customer_repo"]
        )
        container.register(
            "list_customers_handler",
            "core.application.handlers.customers.ListCustomersQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["customer_repo"]
        )
        container.register(
            "search_customers_handler",
            "core.application.handlers.customers.SearchCustomersQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["customer_repo"]
        )
        
        # ✅ ✅ ✅ الإصلاح: معامل واحد فقط (uow)
        container.register(
            "get_customer_statement_handler",
            "core.application.handlers.customers.GetCustomerStatementQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]  # ✅ معامل واحد فقط
        )
        
        # ========== ✅ Customer Branch Query Handlers (جديد) ==========
        container.register(
            "get_branch_handler",
            "core.application.handlers.customer_branch.GetBranchHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "list_branches_handler",
            "core.application.handlers.customer_branch.ListBranchesHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_branch_by_code_handler",
            "core.application.handlers.customer_branch.GetBranchByCodeHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_default_branch_handler",
            "core.application.handlers.customer_branch.GetDefaultBranchHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "search_branches_handler",
            "core.application.handlers.customer_branch.SearchBranchesHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Customer Command Handlers ==========
            try:
                command_bus.register("CreateCustomerCommand", "create_customer_handler")
                logger.info("✅ Registered CreateCustomerCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateCustomerCommand: {e}")
            
            try:
                command_bus.register("UpdateCustomerCommand", "update_customer_handler")
                logger.info("✅ Registered UpdateCustomerCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateCustomerCommand: {e}")
            
            try:
                command_bus.register("ChangeCustomerStatusCommand", "change_customer_status_handler")
                logger.info("✅ Registered ChangeCustomerStatusCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ChangeCustomerStatusCommand: {e}")
            
            try:
                command_bus.register("DeleteCustomerCommand", "delete_customer_handler")
                logger.info("✅ Registered DeleteCustomerCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteCustomerCommand: {e}")
            
            # ========== ✅ Customer Branch Command Handlers (جديد) ==========
            try:
                command_bus.register("CreateBranchCommand", "create_branch_handler")
                logger.info("✅ Registered CreateBranchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateBranchCommand: {e}")
            
            try:
                command_bus.register("UpdateBranchCommand", "update_branch_handler")
                logger.info("✅ Registered UpdateBranchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateBranchCommand: {e}")
            
            try:
                command_bus.register("DeleteBranchCommand", "delete_branch_handler")
                logger.info("✅ Registered DeleteBranchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteBranchCommand: {e}")
            
            try:
                command_bus.register("ActivateBranchCommand", "activate_branch_handler")
                logger.info("✅ Registered ActivateBranchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ActivateBranchCommand: {e}")
            
            try:
                command_bus.register("DeactivateBranchCommand", "deactivate_branch_handler")
                logger.info("✅ Registered DeactivateBranchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeactivateBranchCommand: {e}")
            
            try:
                command_bus.register("SetDefaultBranchCommand", "set_default_branch_handler")
                logger.info("✅ Registered SetDefaultBranchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register SetDefaultBranchCommand: {e}")
            
            # ========== Customer Query Handlers ==========
            try:
                query_bus.register("GetCustomerQuery", "get_customer_handler")
                logger.info("✅ Registered GetCustomerQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCustomerQuery: {e}")
            
            try:
                query_bus.register("ListCustomersQuery", "list_customers_handler")
                logger.info("✅ Registered ListCustomersQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListCustomersQuery: {e}")
            
            try:
                query_bus.register("SearchCustomersQuery", "search_customers_handler")
                logger.info("✅ Registered SearchCustomersQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register SearchCustomersQuery: {e}")
            
            # ✅ ✅ ✅ الإصلاح: تسجيل GetCustomerStatementQuery مع uow فقط
            try:
                query_bus.register("GetCustomerStatementQuery", "get_customer_statement_handler")
                logger.info("✅ Registered GetCustomerStatementQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCustomerStatementQuery: {e}")
            
            # ========== ✅ Customer Branch Query Handlers (جديد) ==========
            try:
                query_bus.register("GetBranchQuery", "get_branch_handler")
                logger.info("✅ Registered GetBranchQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetBranchQuery: {e}")
            
            try:
                query_bus.register("ListBranchesQuery", "list_branches_handler")
                logger.info("✅ Registered ListBranchesQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListBranchesQuery: {e}")
            
            try:
                query_bus.register("GetBranchByCodeQuery", "get_branch_by_code_handler")
                logger.info("✅ Registered GetBranchByCodeQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetBranchByCodeQuery: {e}")
            
            try:
                query_bus.register("GetDefaultBranchQuery", "get_default_branch_handler")
                logger.info("✅ Registered GetDefaultBranchQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetDefaultBranchQuery: {e}")
            
            try:
                query_bus.register("SearchBranchesQuery", "search_branches_handler")
                logger.info("✅ Registered SearchBranchesQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register SearchBranchesQuery: {e}")