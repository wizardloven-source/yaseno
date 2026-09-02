# core/application/handlers/currency/__init__.py

from .create_currency_handler import CreateCurrencyHandler
from .update_currency_handler import UpdateCurrencyHandler
from .delete_currency_handler import DeleteCurrencyHandler
from .set_exchange_rate_handler import SetExchangeRateHandler
from .set_base_currency_handler import SetBaseCurrencyHandler
from .update_exchange_rates_handler import UpdateExchangeRatesHandler
from .fetch_exchange_rates_handler import FetchExchangeRatesHandler
from .get_currency_query_handler import GetCurrencyQueryHandler
from .get_currency_by_code_query_handler import GetCurrencyByCodeQueryHandler
from .list_currencies_query_handler import ListCurrenciesQueryHandler
from .get_base_currency_query_handler import GetBaseCurrencyQueryHandler
from .get_exchange_rate_query_handler import GetExchangeRateQueryHandler  # ✅ إضافة
from .convert_currency_query_handler import ConvertCurrencyQueryHandler  # ✅ إضافة
from .get_exchange_rate_history_query_handler import GetExchangeRateHistoryQueryHandler  # ✅ إضافة

__all__ = [
    "CreateCurrencyHandler",
    "UpdateCurrencyHandler",
    "DeleteCurrencyHandler",
    "SetExchangeRateHandler",
    "SetBaseCurrencyHandler",
    "UpdateExchangeRatesHandler",
    "FetchExchangeRatesHandler",
    "GetCurrencyQueryHandler",
    "GetCurrencyByCodeQueryHandler",
    "ListCurrenciesQueryHandler",
    "GetBaseCurrencyQueryHandler",
    "GetExchangeRateQueryHandler",  # ✅ إضافة
    "ConvertCurrencyQueryHandler",  # ✅ إضافة
    "GetExchangeRateHistoryQueryHandler",  # ✅ إضافة
]