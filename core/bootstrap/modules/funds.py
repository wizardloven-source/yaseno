"""
وحدة الصناديق النقدية - تسجيل جميع خدمات الصناديق
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class FundsModule(Module):
    """وحدة الصناديق النقدية - إدارة الصناديق والتحويلات"""
    
    name = "funds"
    description = "إدارة الصناديق النقدية، الإيداعات، السحوبات، والتحويلات"
    dependencies = ["database", "accounting"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الصناديق"""
        
        # ========== Repositories (Scoped - تعتمد على session) ==========
        container.register_scoped(
            "fund_repo",
            "core.infrastructure.db.postgres.funds_repository.PostgresFundRepository",
            dependencies=["session"]  # ✅ إضافة session
        )
        container.register_scoped(
            "fund_movement_repo",
            "core.infrastructure.db.postgres.funds_repository.PostgresFundMovementRepository",
            dependencies=["session"]  # ✅ إضافة session
        )
        container.register_scoped(
            "fund_transfer_repo",
            "core.infrastructure.db.postgres.funds_repository.PostgresFundTransferRepository",
            dependencies=["session"]  # ✅ إضافة session
        )
        
        # ========== Services (Scoped - جلسة لكل طلب) ==========
        container.register_scoped(
            "fund_service",
            "core.application.funds.services.FundService",
            dependencies=["fund_repo", "fund_movement_repo", "fund_transfer_repo", "uow"]
        )
        
        # ========== Command Handlers (Transient) ==========
        container.register_transient(
            "create_fund_handler",
            "core.application.handlers.funds.CreateFundHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "update_fund_handler",
            "core.application.handlers.funds.UpdateFundHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "delete_fund_handler",
            "core.application.handlers.funds.DeleteFundHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "deposit_fund_handler",
            "core.application.handlers.funds.DepositFundHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "withdraw_fund_handler",
            "core.application.handlers.funds.WithdrawFundHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "transfer_funds_handler",
            "core.application.handlers.funds.TransferFundsHandler",
            dependencies=["uow", "accounting_orchestrator", "posting_engine"]
        )
        
        # ========== Query Handlers (Transient) ==========
        container.register_transient(
            "get_fund_handler",
            "core.application.handlers.funds.GetFundQueryHandler",
            dependencies=["fund_repo"]
        )
        container.register_transient(
            "get_fund_by_code_handler",
            "core.application.handlers.funds.GetFundByCodeQueryHandler",
            dependencies=["fund_repo"]
        )
        container.register_transient(
            "list_funds_handler",
            "core.application.handlers.funds.ListFundsQueryHandler",
            dependencies=["fund_repo"]
        )
        container.register_transient(
            "get_fund_movements_handler",
            "core.application.handlers.funds.GetFundMovementsQueryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "get_fund_balance_handler",
            "core.application.handlers.funds.GetFundBalanceHandler",
            dependencies=["fund_repo"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreateFundCommand", "create_fund_handler")
                logger.info("✅ Registered CreateFundCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateFundCommand: {e}")
            
            try:
                command_bus.register("UpdateFundCommand", "update_fund_handler")
                logger.info("✅ Registered UpdateFundCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateFundCommand: {e}")
            
            try:
                command_bus.register("DeleteFundCommand", "delete_fund_handler")
                logger.info("✅ Registered DeleteFundCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteFundCommand: {e}")
            
            try:
                command_bus.register("DepositToFundCommand", "deposit_fund_handler")
                logger.info("✅ Registered DepositToFundCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DepositToFundCommand: {e}")
            
            try:
                command_bus.register("WithdrawFromFundCommand", "withdraw_fund_handler")
                logger.info("✅ Registered WithdrawFromFundCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register WithdrawFromFundCommand: {e}")
            
            try:
                command_bus.register("TransferBetweenFundsCommand", "transfer_funds_handler")
                logger.info("✅ Registered TransferBetweenFundsCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register TransferBetweenFundsCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetFundQuery", "get_fund_handler")
                logger.info("✅ Registered GetFundQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetFundQuery: {e}")
            
            try:
                query_bus.register("GetFundByCodeQuery", "get_fund_by_code_handler")
                logger.info("✅ Registered GetFundByCodeQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetFundByCodeQuery: {e}")
            
            try:
                query_bus.register("ListFundsQuery", "list_funds_handler")
                logger.info("✅ Registered ListFundsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListFundsQuery: {e}")
            
            try:
                query_bus.register("GetFundMovementsQuery", "get_fund_movements_handler")
                logger.info("✅ Registered GetFundMovementsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetFundMovementsQuery: {e}")
            
            try:
                query_bus.register("GetFundBalanceQuery", "get_fund_balance_handler")
                logger.info("✅ Registered GetFundBalanceQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetFundBalanceQuery: {e}")