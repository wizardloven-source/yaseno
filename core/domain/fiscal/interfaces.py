"""
Fiscal Year Interfaces - واجهات السنة المالية
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date, datetime

from .value_objects import FiscalYearId, FiscalYearCode, FiscalYearStatus, FiscalPeriodReference
from .entities import FiscalYear, FiscalPeriod


class IFiscalYearRepository(ABC):
    """واجهة مستودع السنة المالية"""
    
    @abstractmethod
    def save(self, fiscal_year: FiscalYear) -> None:
        """حفظ السنة المالية"""
        pass
    
    @abstractmethod
    def get_by_id(self, fiscal_year_id: FiscalYearId) -> Optional[FiscalYear]:
        """الحصول على سنة مالية بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_code(self, code: FiscalYearCode) -> Optional[FiscalYear]:
        """الحصول على سنة مالية بواسطة الكود"""
        pass
    
    @abstractmethod
    def get_current(self) -> Optional[FiscalYear]:
        """الحصول على السنة المالية الحالية"""
        pass
    
    @abstractmethod
    def get_all(self, include_closed: bool = False, include_archived: bool = False) -> List[FiscalYear]:
        """الحصول على جميع السنوات المالية"""
        pass
    
    @abstractmethod
    def get_by_year(self, year: int) -> Optional[FiscalYear]:
        """الحصول على سنة مالية بواسطة السنة"""
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: date, end_date: date) -> List[FiscalYear]:
        """الحصول على السنوات المالية في نطاق زمني"""
        pass
    
    @abstractmethod
    def get_overlapping(self, start_date: date, end_date: date, exclude_id: Optional[FiscalYearId] = None) -> Optional[FiscalYear]:
        """الحصول على سنة مالية متداخلة مع التواريخ المحددة"""
        pass
    
    @abstractmethod
    def delete(self, fiscal_year_id: FiscalYearId) -> bool:
        """حذف سنة مالية"""
        pass


class IFiscalPeriodRepository(ABC):
    """واجهة مستودع الفترات المالية"""
    
    @abstractmethod
    def save(self, period: FiscalPeriod) -> None:
        """حفظ فترة مالية"""
        pass
    
    @abstractmethod
    def get_by_id(self, period_id: str) -> Optional[FiscalPeriod]:
        """الحصول على فترة مالية بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_reference(self, reference: FiscalPeriodReference) -> Optional[FiscalPeriod]:
        """الحصول على فترة مالية بواسطة المرجع"""
        pass
    
    @abstractmethod
    def get_by_date(self, dt: date) -> Optional[FiscalPeriod]:
        """الحصول على الفترة المالية التي تحتوي على تاريخ معين"""
        pass
    
    @abstractmethod
    def get_by_year(self, year: int) -> List[FiscalPeriod]:
        """الحصول على جميع فترات سنة معينة"""
        pass
    
    @abstractmethod
    def get_open_periods(self, fiscal_year_id: Optional[str] = None) -> List[FiscalPeriod]:
        """الحصول على الفترات المفتوحة"""
        pass
    
    @abstractmethod
    def get_closed_periods(self, fiscal_year_id: Optional[str] = None) -> List[FiscalPeriod]:
        """الحصول على الفترات المغلقة"""
        pass
    
    @abstractmethod
    def delete(self, period_id: str) -> bool:
        """حذف فترة مالية"""
        pass