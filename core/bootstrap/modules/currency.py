# core/bootstrap/modules/currency.py
"""
وحدة العملات - تسجيل جميع خدمات العملات
مستخرجة من bootstrap.py
"""

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module


class CurrencyModule(Module):
    """
    وحدة العملات - إدارة العملات وأسعار الصرف
    
    تشمل:
        1. عملات متعددة (USD, EUR, LBP, GBP, ...)
        2. أسعار صرف ديناميكية
        3. عملة أساسية للنظام
        4. تحويل العملات التلقائي
        5. تحديث أسعار الصرف من الإنترنت
    """
    
    name = "currency"
    description = "إدارة العملات وأسعار الصرف - دعم متعدد العملات"
    dependencies = ["database"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات العملات"""
        
        # ========== Repository ==========
        container.register(
            "currency_repo",
            "core.infrastructure.db.postgres.currency_repository.PostgresCurrencyRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ تم الإصلاح: إضافة session كاعتماد
        )
        
        # ========== Services ==========
        container.register(
            "currency_service",
            "core.application.currency.services.CurrencyService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["currency_repo", "uow"]
        )
        container.register(
            "exchange_rate_service",
            "core.application.currency.services.ExchangeRateService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["currency_repo", "uow"]
        )
        container.register(
            "currency_converter",
            "core.application.currency.services.CurrencyConverter",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["currency_repo", "exchange_rate_service"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_currency_handler",
            "core.application.handlers.currency.CreateCurrencyHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_currency_handler",
            "core.application.handlers.currency.UpdateCurrencyHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_currency_handler",
            "core.application.handlers.currency.DeleteCurrencyHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "set_exchange_rate_handler",
            "core.application.handlers.currency.SetExchangeRateHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "set_base_currency_handler",
            "core.application.handlers.currency.SetBaseCurrencyHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_exchange_rates_handler",
            "core.application.handlers.currency.UpdateExchangeRatesHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "exchange_rate_service"]
        )
        container.register(
            "fetch_exchange_rates_handler",
            "core.application.handlers.currency.FetchExchangeRatesHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "exchange_rate_service"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_currency_handler",
            "core.application.handlers.currency.GetCurrencyQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_currency_by_code_handler",
            "core.application.handlers.currency.GetCurrencyByCodeQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "list_currencies_handler",
            "core.application.handlers.currency.ListCurrenciesQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_base_currency_handler",
            "core.application.handlers.currency.GetBaseCurrencyQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_exchange_rate_handler",
            "core.application.handlers.currency.GetExchangeRateQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["currency_repo"]
        )
        container.register(
            "convert_currency_handler",
            "core.application.handlers.currency.ConvertCurrencyQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["currency_converter"]
        )
        container.register(
            "get_exchange_rate_history_handler",
            "core.application.handlers.currency.GetExchangeRateHistoryQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["currency_repo"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ========== Command Handlers ==========
        command_bus.register("CreateCurrencyCommand", "create_currency_handler")
        command_bus.register("UpdateCurrencyCommand", "update_currency_handler")
        command_bus.register("DeleteCurrencyCommand", "delete_currency_handler")
        command_bus.register("SetExchangeRateCommand", "set_exchange_rate_handler")
        command_bus.register("SetBaseCurrencyCommand", "set_base_currency_handler")
        command_bus.register("UpdateExchangeRatesCommand", "update_exchange_rates_handler")
        command_bus.register("FetchExchangeRatesCommand", "fetch_exchange_rates_handler")
        
        # ========== Query Handlers ==========
        query_bus.register("GetCurrencyQuery", "get_currency_handler")
        query_bus.register("GetCurrencyByCodeQuery", "get_currency_by_code_handler")
        query_bus.register("ListCurrenciesQuery", "list_currencies_handler")
        query_bus.register("GetBaseCurrencyQuery", "get_base_currency_handler")
        query_bus.register("GetExchangeRateQuery", "get_exchange_rate_handler")
        query_bus.register("ConvertCurrencyQuery", "convert_currency_handler")
        query_bus.register("GetExchangeRateHistoryQuery", "get_exchange_rate_history_handler")