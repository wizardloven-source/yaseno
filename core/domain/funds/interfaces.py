# core/domain/funds/interfaces.py
"""
Repository Interfaces for Funds Context
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date, datetime

from .entities import Fund, FundTransaction, FundTransfer
from .value_objects import FundId, FundCode, FundType, TransactionType, TransferStatus
FundMovement = FundTransaction


class IFundRepository(ABC):
    """واجهة مستودع الصناديق"""
    
    @abstractmethod
    def save(self, fund: Fund) -> None:
        """حفظ الصندوق (جديد أو محدث)"""
        pass
    
    @abstractmethod
    def get_by_id(self, fund_id: FundId, include_transactions: bool = False) -> Optional[Fund]:
        """الحصول على صندوق بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_code(self, code: FundCode, include_transactions: bool = False) -> Optional[Fund]:
        """الحصول على صندوق بواسطة الكود"""
        pass
    
    @abstractmethod
    def get_by_account_code(self, account_code: str) -> Optional[Fund]:
        """الحصول على صندوق بواسطة كود حساب الأستاذ"""
        pass
    
    @abstractmethod
    def list_all(
        self,
        fund_type: Optional[FundType] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
        include_balance: bool = True
    ) -> List[Fund]:
        """قائمة جميع الصناديق"""
        pass
    
    @abstractmethod
    def get_active_funds(self) -> List[Fund]:
        """الحصول على الصناديق النشطة فقط"""
        pass
    
    @abstractmethod
    def get_funds_by_currency(self, currency: str) -> List[Fund]:
        """الحصول على الصناديق بعملة محددة"""
        pass
    
    @abstractmethod
    def get_next_code(self, prefix: str = "F") -> str:
        """توليد كود صندوق تلقائي"""
        pass
    
    @abstractmethod
    def delete(self, fund_id: FundId, permanent: bool = False) -> bool:
        """حذف صندوق (ناعم أو دائم)"""
        pass
    
    @abstractmethod
    def exists_by_code(self, code: FundCode) -> bool:
        """التحقق من وجود صندوق بالكود"""
        pass
    
    @abstractmethod
    def get_balance(self, fund_id: FundId, as_of: Optional[datetime] = None) -> 'Money':
        """الحصول على رصيد الصندوق (محسوب من الحركات)"""
        pass
    
    @abstractmethod
    def get_balance_history(
        self,
        fund_id: FundId,
        from_date: datetime,
        to_date: datetime
    ) -> List[tuple]:
        """الحصول على تاريخ الرصيد بين تاريخين"""
        pass


class IFundTransactionRepository(ABC):
    """واجهة مستودع حركات الصندوق (الإصدار الجديد)"""
    
    @abstractmethod
    def save(self, transaction: FundTransaction, fund_id: FundId) -> None:
        """حفظ حركة صندوق"""
        pass
    
    @abstractmethod
    def get_by_id(self, transaction_id: str) -> Optional[FundTransaction]:
        """الحصول على حركة بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_fund(self, fund_id: FundId, limit: int = 100, offset: int = 0) -> List[FundTransaction]:
        """الحصول على حركات صندوق معين"""
        pass
    
    @abstractmethod
    def get_by_date_range(
        self,
        fund_id: FundId,
        from_date: datetime,
        to_date: datetime,
        transaction_type: Optional[TransactionType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundTransaction]:
        """الحصول على حركات في نطاق زمني"""
        pass
    
    @abstractmethod
    def get_by_reference(self, reference_id: str) -> List[FundTransaction]:
        """الحصول على الحركات المرتبطة بمرجع معين (مثل رقم القيد المحاسبي)"""
        pass
    
    @abstractmethod
    def delete(self, transaction_id: str) -> bool:
        """حذف حركة صندوق"""
        pass


class IFundTransferRepository(ABC):
    """واجهة مستودع عمليات التحويل"""
    
    @abstractmethod
    def save(self, transfer: FundTransfer) -> None:
        """حفظ عملية تحويل"""
        pass
    
    @abstractmethod
    def get_by_id(self, transfer_id: str) -> Optional[FundTransfer]:
        """الحصول على تحويل بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_funds(
        self,
        from_fund_id: FundId,
        to_fund_id: FundId,
        status: Optional[TransferStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundTransfer]:
        """الحصول على التحويلات بين صندوقين"""
        pass
    
    @abstractmethod
    def get_by_fund(self, fund_id: FundId, status: Optional[TransferStatus] = None, limit: int = 100) -> List[FundTransfer]:
        """الحصول على التحويلات المرتبطة بصندوق (كمصدر أو هدف)"""
        pass
    
    @abstractmethod
    def get_by_status(self, status: TransferStatus, limit: int = 100) -> List[FundTransfer]:
        """الحصول على التحويلات حسب الحالة"""
        pass
    
    @abstractmethod
    def get_by_date_range(
        self,
        from_date: datetime,
        to_date: datetime,
        status: Optional[TransferStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundTransfer]:
        """الحصول على التحويلات في نطاق زمني"""
        pass
    
    @abstractmethod
    def get_pending_transfers(self, limit: int = 100) -> List[FundTransfer]:
        """الحصول على التحويلات المعلقة (Pending)"""
        pass
    
    @abstractmethod
    def update_status(self, transfer_id: str, status: TransferStatus, updated_by: str) -> bool:
        """تحديث حالة التحويل"""
        pass


# ========== الواجهات القديمة للتوافق ==========

class IFundMovementRepository(ABC):
    """واجهة مستودع حركات الصندوق (للتوافق مع الكود القديم)"""
    
    @abstractmethod
    def save(self, movement: FundMovement) -> None:
        """حفظ حركة صندوق"""
        pass
    
    @abstractmethod
    def get_by_id(self, movement_id: str) -> Optional[FundMovement]:
        """الحصول على حركة بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_fund(self, fund_id: FundId, limit: int = 100) -> List[FundMovement]:
        """الحصول على حركات صندوق معين"""
        pass
    
    @abstractmethod
    def get_by_date_range(
        self,
        fund_id: FundId,
        from_date: date,
        to_date: date,
        movement_type: Optional['MovementType'] = None
    ) -> List[FundMovement]:
        """الحصول على حركات في نطاق زمني"""
        pass
    
    @abstractmethod
    def delete(self, movement_id: str) -> bool:
        """حذف حركة صندوق"""
        pass