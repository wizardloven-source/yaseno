# core/bootstrap/modules/invoicing.py
"""
وحدة الفواتير - تسجيل جميع خدمات الفواتير
مستخرجة من bootstrap.py
"""

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module


class InvoicingModule(Module):
    """وحدة الفواتير - إدارة المبيعات والفواتير"""
    
    name = "invoicing"
    description = "إدارة الفواتير، المبيعات، والمرتجعات"
    dependencies = ["database", "accounting", "inventory", "customers", "funds"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الفواتير"""
        
        # ========== Repositories ==========
        container.register(
            "invoice_repo",
            "core.infrastructure.db.postgres.repositories_invoice.PostgresInvoiceRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ إضافة session
        )
        container.register(
            "invoice_line_repo",
            "core.infrastructure.db.postgres.repositories_invoice.PostgresInvoiceLineRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ إضافة session
        )
        
        # ========== Services ==========
        container.register(
            "invoice_service",
            "core.application.invoicing.services.InvoiceService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["invoice_repo", "uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_invoice_handler",
            "core.application.handlers.invoicing.CreateInvoiceHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "add_invoice_line_handler",
            "core.application.handlers.invoicing.AddInvoiceLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_invoice_line_handler",
            "core.application.handlers.invoicing.UpdateInvoiceLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "remove_invoice_line_handler",
            "core.application.handlers.invoicing.RemoveInvoiceLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "clear_invoice_lines_handler",
            "core.application.handlers.invoicing.ClearInvoiceLinesHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ✅ تم التصحيح: استخدام accounting_orchestrator بدلاً من stock_service و fund_service
        container.register(
            "post_invoice_handler",
            "core.application.handlers.invoicing.PostInvoiceHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "accounting_orchestrator", "posting_engine"]
        )
        
        container.register(
            "delete_draft_invoice_handler",
            "core.application.handlers.invoicing.DeleteDraftInvoiceHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "cancel_invoice_handler",
            "core.application.handlers.invoicing.CancelInvoiceHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "posting_engine"]
        )
        container.register(
            "return_invoice_handler",
            "core.application.handlers.invoicing.ReturnInvoiceHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "posting_engine", "stock_service"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_invoice_handler",
            "core.application.handlers.invoicing.GetInvoiceQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["invoice_repo"]  # ✅ هذا سيعمل الآن لأن invoice_repo له session
        )
        container.register(
            "list_invoices_handler",
            "core.application.handlers.invoicing.ListInvoicesQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["invoice_repo"]
        )
        container.register(
            "get_customer_invoices_handler",
            "core.application.handlers.invoicing.GetCustomerInvoicesQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["invoice_repo"]
        )
        container.register(
            "get_invoice_stats_handler",
            "core.application.handlers.invoicing.GetInvoiceStatsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["invoice_repo"]
        )
        container.register(
            "search_invoices_handler",
            "core.application.handlers.invoicing.SearchInvoicesQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["invoice_repo"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ========== Command Handlers ==========
        command_bus.register("CreateInvoiceCommand", "create_invoice_handler")
        command_bus.register("AddInvoiceLineCommand", "add_invoice_line_handler")
        command_bus.register("UpdateInvoiceLineCommand", "update_invoice_line_handler")
        command_bus.register("RemoveInvoiceLineCommand", "remove_invoice_line_handler")
        command_bus.register("ClearInvoiceLinesCommand", "clear_invoice_lines_handler")
        command_bus.register("PostInvoiceCommand", "post_invoice_handler")
        command_bus.register("DeleteDraftInvoiceCommand", "delete_draft_invoice_handler")
        command_bus.register("CancelInvoiceCommand", "cancel_invoice_handler")
        command_bus.register("ReturnInvoiceCommand", "return_invoice_handler")
        
        # ========== Query Handlers ==========
        query_bus.register("GetInvoiceQuery", "get_invoice_handler")
        query_bus.register("ListInvoicesQuery", "list_invoices_handler")
        query_bus.register("GetCustomerInvoicesQuery", "get_customer_invoices_handler")
        query_bus.register("GetInvoiceStatsQuery", "get_invoice_stats_handler")
        query_bus.register("SearchInvoicesQuery", "search_invoices_handler")