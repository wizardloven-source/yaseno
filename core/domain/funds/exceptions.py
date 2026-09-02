# core/domain/funds/exceptions.py
"""
Domain Exceptions for Funds Context
"""


class FundError(Exception):
    """Base exception for funds domain"""
    pass


class FundNotFoundError(FundError):
    """يُرفع عندما لا يتم العثور على الصندوق"""
    def __init__(self, fund_id: str):
        self.fund_id = fund_id
        super().__init__(f"Fund not found: {fund_id}")


class DuplicateFundCodeError(FundError):
    """يُرفع عند محاولة إنشاء صندوق بكود مكرر"""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Fund code already exists: {code}")


class InsufficientFundsError(FundError):
    """يُرفع عند محاولة سحب مبلغ أكبر من الرصيد"""
    def __init__(self, fund_code: str, balance: float, requested: float):
        self.fund_code = fund_code
        self.balance = balance
        self.requested = requested
        super().__init__(
            f"Insufficient funds in {fund_code}. Balance: {balance}, Requested: {requested}"
        )


class FundAlreadyActiveError(FundError):
    """يُرفع عند محاولة تنشيط صندوق نشط بالفعل"""
    def __init__(self, fund_code: str):
        self.fund_code = fund_code
        super().__init__(f"Fund {fund_code} is already active")


class FundAlreadyInactiveError(FundError):
    """يُرفع عند محاولة تعطيل صندوق غير نشط"""
    def __init__(self, fund_code: str):
        self.fund_code = fund_code
        super().__init__(f"Fund {fund_code} is already inactive")


class InvalidFundTypeError(FundError):
    """يُرفع عند استخدام نوع صندوق غير صالح"""
    def __init__(self, fund_type: str):
        self.fund_type = fund_type
        super().__init__(f"Invalid fund type: {fund_type}")


class CannotDeleteFundWithMovementsError(FundError):
    """يُرفع عند محاولة حذف صندوق له حركات"""
    def __init__(self, fund_code: str, movements_count: int):
        self.fund_code = fund_code
        self.movements_count = movements_count
        super().__init__(
            f"Cannot delete fund {fund_code} because it has {movements_count} movements"
        )


class FundTransferError(FundError):
    """يُرفع عند حدوث خطأ في التحويل بين الصناديق"""
    def __init__(self, message: str):
        super().__init__(f"Transfer error: {message}")


class SameFundTransferError(FundError):
    """يُرفع عند محاولة تحويل من وإلى نفس الصندوق"""
    def __init__(self, fund_code: str):
        self.fund_code = fund_code
        super().__init__(f"Cannot transfer to/from the same fund: {fund_code}")


# ========== الاستثناءات الجديدة المطلوبة ==========

class FundClosedError(FundError):
    """يُرفع عند محاولة إجراء عملية على صندوق مغلق"""
    def __init__(self, fund_code: str):
        self.fund_code = fund_code
        super().__init__(f"Fund {fund_code} is closed. No transactions allowed.")


class FundSuspendedError(FundError):
    """يُرفع عند محاولة إجراء عملية على صندوق معلق"""
    def __init__(self, fund_code: str):
        self.fund_code = fund_code
        super().__init__(f"Fund {fund_code} is suspended. No transactions allowed.")


class InvalidTransactionError(FundError):
    """يُرفع عند محاولة إضافة حركة غير صالحة"""
    def __init__(self, message: str):
        super().__init__(f"Invalid transaction: {message}")


class DuplicateTransactionError(FundError):
    """يُرفع عند محاولة إضافة حركة مكررة"""
    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id
        super().__init__(f"Transaction {transaction_id} already exists")


class DailyLimitExceededError(FundError):
    """يُرفع عند تجاوز الحد اليومي للسحوبات"""
    def __init__(self, fund_code: str, limit: float, attempted: float):
        self.fund_code = fund_code
        self.limit = limit
        self.attempted = attempted
        super().__init__(
            f"Daily withdrawal limit exceeded for fund {fund_code}. "
            f"Limit: {limit}, Attempted: {attempted}"
        )


class MonthlyLimitExceededError(FundError):
    """يُرفع عند تجاوز الحد الشهري للسحوبات"""
    def __init__(self, fund_code: str, limit: float, attempted: float):
        self.fund_code = fund_code
        self.limit = limit
        self.attempted = attempted
        super().__init__(
            f"Monthly withdrawal limit exceeded for fund {fund_code}. "
            f"Limit: {limit}, Attempted: {attempted}"
        )


class CurrencyMismatchError(FundError):
    """يُرفع عند محاولة إجراء عملية بعملة مختلفة عن عملة الصندوق"""
    def __init__(self, fund_currency: str, transaction_currency: str):
        self.fund_currency = fund_currency
        self.transaction_currency = transaction_currency
        super().__init__(
            f"Currency mismatch: Fund currency is {fund_currency}, "
            f"but transaction currency is {transaction_currency}"
        )


class ExchangeRateNotFoundError(FundError):
    """يُرفع عند عدم وجود سعر صرف للعملات المطلوبة"""
    def __init__(self, from_currency: str, to_currency: str):
        self.from_currency = from_currency
        self.to_currency = to_currency
        super().__init__(f"Exchange rate not found: {from_currency} -> {to_currency}")


class ApprovalRequiredError(FundError):
    """يُرفع عند الحاجة إلى موافقة على عملية"""
    def __init__(self, fund_code: str, amount: float):
        self.fund_code = fund_code
        self.amount = amount
        super().__init__(
            f"Approval required for transaction of {amount} on fund {fund_code}"
        )


class InvalidAmountError(FundError):
    """يُرفع عند استخدام مبلغ غير صالح"""
    def __init__(self, message: str):
        super().__init__(f"Invalid amount: {message}")


# ========== تحديث __all__ ==========

__all__ = [
    # الاستثناءات الأساسية
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
    # الاستثناءات الجديدة
    "FundClosedError",
    "FundSuspendedError",
    "InvalidTransactionError",
    "DuplicateTransactionError",
    "DailyLimitExceededError",
    "MonthlyLimitExceededError",
    "CurrencyMismatchError",
    "ExchangeRateNotFoundError",
    "ApprovalRequiredError",
    "InvalidAmountError",
]