# core/application/handlers/funds/__init__.py
"""
Funds Handlers - معالجات أوامر واستعلامات الصناديق
"""

from .create_fund_handler import CreateFundHandler
from .update_fund_handler import UpdateFundHandler
from .delete_fund_handler import DeleteFundHandler
from .deposit_fund_handler import DepositFundHandler
from .withdraw_fund_handler import WithdrawFundHandler
from .transfer_funds_handler import TransferFundsHandler
from .get_fund_query_handler import GetFundQueryHandler
from .get_fund_by_code_query_handler import GetFundByCodeQueryHandler
from .list_funds_query_handler import ListFundsQueryHandler
from .get_fund_movements_query_handler import GetFundMovementsQueryHandler
from .get_fund_balance_handler import GetFundBalanceHandler  # أضف هذا

__all__ = [
    "CreateFundHandler",
    "UpdateFundHandler",
    "DeleteFundHandler",
    "DepositFundHandler",
    "WithdrawFundHandler",
    "TransferFundsHandler",
    "GetFundQueryHandler",
    "GetFundByCodeQueryHandler",
    "ListFundsQueryHandler",
    "GetFundMovementsQueryHandler",
    "GetFundBalanceHandler",  # أضف هذا
]