# core/bootstrap/modules/accounting.py
"""
وحدة المحاسبة - تسجيل جميع خدمات المحاسبة
الإصدار المُصلح - v2.0.2
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class AccountingModule(Module):
    """وحدة المحاسبة - القلب النابض للنظام"""
    
    name = "accounting"
    description = "المحرك المحاسبي - القيود اليومية، دفتر الأستاذ، الإقفال"
    dependencies = ["database", "fiscal", "security"]
    version = "2.0.2"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات المحاسبة"""
        
        # ========== Repositories (تتطلب session) ==========
        container.register_scoped(
            "journal_repo",
            "core.infrastructure.db.postgres.repositories.PostgresJournalEntryRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "ledger_repo",
            "core.infrastructure.db.postgres.repositories.PostgresLedgerRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "account_repo",
            "core.infrastructure.db.postgres.repositories.PostgresAccountRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "period_repo",
            "core.infrastructure.db.postgres.repositories.PostgresFiscalPeriodRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "audit_repo",
            "core.infrastructure.db.postgres.repositories.PostgresAuditRepository",
            dependencies=["session"]
        )
        
        # ========== ✅ Rule Engine Repositories ==========
        container.register_scoped(
            "rule_repo",
            "core.infrastructure.db.postgres.rule_repository.PostgresRuleRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "rule_group_repo",
            "core.infrastructure.db.postgres.rule_repository.PostgresRuleGroupRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "rule_log_repo",
            "core.infrastructure.db.postgres.rule_repository.PostgresRuleExecutionLogRepository",
            dependencies=["session"]
        )
        
        # ========== ✅ Rule Engine (بدون تبعية دائرية) ==========
        container.register_scoped(
            "rule_engine",
            "core.domain.rules.services.RuleEngine",
            dependencies=["rule_repo", "rule_group_repo", "rule_log_repo"]
        )
        
        # ========== Domain Services (Scoped - جلسة لكل طلب) ==========
        container.register_scoped(
            "posting_engine",
            "core.domain.accounting.posting_engine.PostingEngine",
            dependencies=["journal_repo", "ledger_repo", "period_repo", "account_repo", "uow", "fiscal_service"]
        )
        container.register_scoped(
            "ledger_engine",
            "core.domain.accounting.services.LedgerEngine",
            dependencies=["ledger_repo"]
        )
        container.register_scoped(
            "reversal_service",
            "core.domain.accounting.services.ReversalService",
            dependencies=["journal_repo", "posting_engine"]
        )
        
        container.register_scoped(
            "closing_service",
            "core.domain.accounting.services.ClosingService",
            dependencies=["ledger_engine", "posting_engine", "period_repo", "journal_repo", "account_repo", "fiscal_service"]
        )
        
        container.register_scoped(
            "trial_balance_service",
            "core.domain.accounting.services.TrialBalanceService",
            dependencies=["ledger_engine"]
        )
        
        container.register_scoped(
            "reconciliation_service",
            "core.domain.accounting.reconciliation_service.ReconciliationService",
            dependencies=["ledger_repo", "journal_repo", "posting_engine", "ledger_engine", "audit_repo"]
        )
        
        # ========== ✅ Accounting Orchestrator ==========
        container.register_scoped(
            "accounting_orchestrator",
            "core.application.accounting.orchestrator.AccountingOrchestrator",
            dependencies=["uow", "posting_engine", "rule_engine", "tax_engine", "center_service"]
        )
        
        # ========== Command Handlers (Transient) ==========
        container.register_transient(
            "create_journal_entry_handler",
            "core.application.accounting.handlers.CreateJournalEntryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "post_journal_entry_handler",
            "core.application.accounting.handlers.PostJournalEntryHandler",
            dependencies=["uow", "posting_engine"]
        )
        container.register_transient(
            "reverse_journal_entry_handler",
            "core.application.accounting.handlers.ReverseJournalEntryHandler",
            dependencies=["uow", "reversal_service"]
        )
        container.register_transient(
            "close_period_handler",
            "core.application.accounting.handlers.ClosePeriodHandler",
            dependencies=["uow", "closing_service"]
        )
        container.register_transient(
            "open_period_handler",
            "core.application.accounting.handlers.OpenPeriodHandler",
            dependencies=["uow", "closing_service"]
        )
        container.register_transient(
            "create_account_handler",
            "core.application.accounting.handlers.CreateAccountCommandHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "update_account_handler",
            "core.application.accounting.handlers.UpdateAccountCommandHandler",
            dependencies=["uow"]
        )
        
        # ========== Query Handlers (Transient) ==========
        # ✅ جميع Query Handlers تحتاج إلى uow كأول تبعية
        container.register_transient(
            "get_journal_entry_handler",
            "core.application.accounting.handlers.GetJournalEntryQueryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "get_trial_balance_handler",
            "core.application.accounting.handlers.GetTrialBalanceQueryHandler",
            dependencies=["uow", "ledger_engine"]  # ✅ uow + ledger_engine
        )
        container.register_transient(
            "get_account_balance_handler",
            "core.application.accounting.handlers.GetAccountBalanceQueryHandler",
            dependencies=["uow", "ledger_engine"]  # ✅ uow + ledger_engine
        )
        container.register_transient(
            "list_journal_entries_handler",
            "core.application.accounting.handlers.ListJournalEntriesQueryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "get_period_status_handler",
            "core.application.accounting.handlers.GetPeriodStatusQueryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "get_audit_log_handler",
            "core.application.accounting.handlers.GetAuditLogQueryHandler",
            dependencies=["uow"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreateJournalEntryCommand", "create_journal_entry_handler")
                logger.info("✅ Registered CreateJournalEntryCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateJournalEntryCommand: {e}")
            
            try:
                command_bus.register("PostJournalEntryCommand", "post_journal_entry_handler")
                logger.info("✅ Registered PostJournalEntryCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register PostJournalEntryCommand: {e}")
            
            try:
                command_bus.register("ReverseJournalEntryCommand", "reverse_journal_entry_handler")
                logger.info("✅ Registered ReverseJournalEntryCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ReverseJournalEntryCommand: {e}")
            
            try:
                command_bus.register("ClosePeriodCommand", "close_period_handler")
                logger.info("✅ Registered ClosePeriodCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ClosePeriodCommand: {e}")
            
            try:
                command_bus.register("OpenPeriodCommand", "open_period_handler")
                logger.info("✅ Registered OpenPeriodCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register OpenPeriodCommand: {e}")
            
            try:
                command_bus.register("CreateAccountCommand", "create_account_handler")
                logger.info("✅ Registered CreateAccountCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateAccountCommand: {e}")
            
            try:
                command_bus.register("UpdateAccountCommand", "update_account_handler")
                logger.info("✅ Registered UpdateAccountCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateAccountCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetJournalEntryQuery", "get_journal_entry_handler")
                logger.info("✅ Registered GetJournalEntryQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetJournalEntryQuery: {e}")
            
            try:
                query_bus.register("GetTrialBalanceQuery", "get_trial_balance_handler")
                logger.info("✅ Registered GetTrialBalanceQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetTrialBalanceQuery: {e}")
            
            try:
                query_bus.register("GetAccountBalanceQuery", "get_account_balance_handler")
                logger.info("✅ Registered GetAccountBalanceQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetAccountBalanceQuery: {e}")
            
            try:
                query_bus.register("ListJournalEntriesQuery", "list_journal_entries_handler")
                logger.info("✅ Registered ListJournalEntriesQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListJournalEntriesQuery: {e}")
            
            try:
                query_bus.register("GetPeriodStatusQuery", "get_period_status_handler")
                logger.info("✅ Registered GetPeriodStatusQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetPeriodStatusQuery: {e}")
            
            try:
                query_bus.register("GetAuditLogQuery", "get_audit_log_handler")
                logger.info("✅ Registered GetAuditLogQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetAuditLogQuery: {e}")