# core/domain/funds/__init__.py
"""
Funds Bounded Context - Domain Layer
Professional Edition - Transaction-based architecture
"""

from .entities import Fund, FundTransaction, FundTransfer
from .value_objects import (
    FundId, FundCode, FundType, TransactionType, TransferStatus, FundStatus,
    Money, FundLimits, ExchangeRate, TransactionId, TransferId, DateRange
)
from .events import (
    FundCreatedEvent,
    FundUpdatedEvent,
    FundDeletedEvent,
    FundBalanceChangedEvent,
    FundTransferCompletedEvent,
    FundTransactionCreatedEvent,
    FundStatusChangedEvent,
    FundMovementCreatedEvent,
    FundMovementDeletedEvent
)
from .exceptions import (
    FundError,
    FundNotFoundError,
    DuplicateFundCodeError,
    InsufficientFundsError,
    FundAlreadyActiveError,
    FundAlreadyInactiveError,
    InvalidFundTypeError,
    CannotDeleteFundWithMovementsError,
    FundTransferError,
    SameFundTransferError,
    FundClosedError,
    FundSuspendedError,
    InvalidTransactionError,
    DuplicateTransactionError,
    DailyLimitExceededError,
    MonthlyLimitExceededError,
    CurrencyMismatchError,
    ExchangeRateNotFoundError,
    ApprovalRequiredError,
)
from .interfaces import (
    IFundRepository,
    IFundTransactionRepository,
    IFundTransferRepository,
    IFundMovementRepository,
)

# للتوافق مع الكود القديم - إعادة توجيه FundMovement إلى FundTransaction
FundMovement = FundTransaction

__all__ = [
    # Entities
    "Fund",
    "FundTransaction",
    "FundTransfer",
    "FundMovement",  # للتوافق مع الكود القديم
    
    # Value Objects
    "FundId",
    "FundCode",
    "FundType",
    "TransactionType",
    "TransferStatus",
    "FundStatus",
    "Money",
    "FundLimits",
    "ExchangeRate",
    "TransactionId",
    "TransferId",
    "DateRange",
    
    # Events
    "FundCreatedEvent",
    "FundUpdatedEvent",
    "FundDeletedEvent",
    "FundBalanceChangedEvent",
    "FundTransferCompletedEvent",
    "FundTransactionCreatedEvent",
    "FundStatusChangedEvent",
    "FundMovementCreatedEvent",
    "FundMovementDeletedEvent",
    
    # Exceptions
    "FundError",
    "FundNotFoundError",
    "DuplicateFundCodeError",
    "InsufficientFundsError",
    "FundAlreadyActiveError",
    "FundAlreadyInactiveError",
    "InvalidFundTypeError",
    "CannotDeleteFundWithMovementsError",
    "FundTransferError",
    "SameFundTransferError",
    "FundClosedError",
    "FundSuspendedError",
    "InvalidTransactionError",
    "DuplicateTransactionError",
    "DailyLimitExceededError",
    "MonthlyLimitExceededError",
    "CurrencyMismatchError",
    "ExchangeRateNotFoundError",
    "ApprovalRequiredError",
    
    # Interfaces
    "IFundRepository",
    "IFundTransactionRepository",
    "IFundTransferRepository",
    "IFundMovementRepository",
]